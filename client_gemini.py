from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastmcp import Client
from google import genai
from google.genai import types
from google.genai import errors
import time


def _load_skill_context(modules_dir: Path) -> str:
    """Load SKILL.md files from all modules and combine them."""
    skill_texts = []

    for module_dir in sorted(modules_dir.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue

        skill_file = module_dir / "SKILL.md"
        if skill_file.exists():
            skill_texts.append(skill_file.read_text())

    return "\n\n---\n\n".join(skill_texts)


def _strip_ctx_from_schema(schema: dict) -> dict:
    schema = dict(schema or {})
    props = dict(schema.get("properties", {}))
    props.pop("ctx", None)
    schema["properties"] = props

    if "required" in schema:
        schema["required"] = [r for r in schema["required"] if r != "ctx"]

    return schema


def _capabilities_to_system_content(mcp_tools, mcp_resources, skill_context: str = "") -> types.Content:
    """Serialize MCP tools and resources into a system message for the LLM."""
    tools_json = []
    for t in mcp_tools:
        tools_json.append({
            "name": t.name,
            "description": getattr(t, "description", ""),
            "input_schema": getattr(t, "inputSchema", None),
        })

    resources_json = []
    for r in mcp_resources:
        uri_obj = getattr(r, "uri", None) or getattr(r, "name", None)
        uri_str = str(uri_obj) if uri_obj is not None else None

        # Extract resource name from URI for easier reference
        resource_name = uri_str.split("/")[-1] if uri_str else None

        resources_json.append({
            "uri": uri_str,
            "name": resource_name,
            "description": getattr(r, "description", ""),
        })

    payload = {
        "mcp_tools": tools_json,
        "mcp_resources": resources_json,
        "instruction": (
            "You may call MCP tools using their schemas. "
            "Tools that operate on sequences accept either a resource name (e.g., 'pBR322') "
            "or a raw DNA sequence string. Prefer using resource names when available. "
            "The server will resolve resource names to their sequences automatically."
        ),
    }

    system_text = "SYSTEM CONTEXT (capabilities, not user input):\n" + json.dumps(payload, indent=2)

    # Add skill context if available
    if skill_context:
        system_text += "\n\n--- SKILL GUIDANCE ---\n\n" + skill_context

    return types.Content(
        role="model",
        parts=[types.Part.from_text(text=system_text)],
    )

def _mcp_tool_to_function_declaration(tool: Any) -> types.FunctionDeclaration:
    """Convert a FastMCP tool definition into a Gemini FunctionDeclaration.

    FastMCP tools typically provide:
      - name
      - description
      - inputSchema (JSON schema for params)
    Gemini expects JSON Schema under parameters_json_schema.
    """
    params: Dict[str, Any] = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    params = _strip_ctx_from_schema(params)
    desc = (getattr(tool, "description", None) or "").strip() or f"MCP tool: {tool.name}"
    return types.FunctionDeclaration(
        name=tool.name,
        description=desc,
        parameters_json_schema=params,
    )


def _prompt_messages_to_gemini_contents(prompt_result: Any) -> List[types.Content]:
    """Convert an MCP prompt render result into Gemini `Content` messages.

    FastMCP `get_prompt()` commonly returns an object with `.messages`, where each message has:
      - role (e.g., "system", "user", "assistant")
      - content (often a list of content parts with `.text`)
    This helper tries to be robust across minor SDK variations.
    """
    msgs = getattr(prompt_result, "messages", None) or getattr(prompt_result, "message", None) or []
    out: List[types.Content] = []

    for m in msgs:
        role = getattr(m, "role", "user") or "user"
        content = getattr(m, "content", None)

        # content may be a string, or a list of TextContent-like objects
        texts: List[str] = []
        if isinstance(content, str):
            texts = [content]
        elif isinstance(content, list):
            for part in content:
                t = getattr(part, "text", None)
                if t is None and isinstance(part, str):
                    t = part
                if t is not None:
                    texts.append(str(t))
        elif content is not None:
            # fallback
            texts = [str(content)]

        if not texts:
            continue

        out.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text="\n".join(texts))],
            )
        )

    return out


def _print_help() -> None:
    print(
        "\nCommands:\n"
        "  /help                         Show this help\n"
        "  /tools                        List tools\n"
        "  /resources                    List resources\n"
        "  /resource <uri>               Read a resource\n"
        "  /prompts                      List prompts\n"
        "  /prompt <name> [json_args]    Render a prompt and run it through Gemini\n"
        "\nExamples:\n"
        "  /resources\n"
        "  /resource resource://crispr_example/protocol_overview\n"
        "  /prompts\n"
        "  /prompt spacer_design_workflow {\"target_sequence\": \"ACGT...\", \"pam\": \"NGG\", \"top_n\": 5}\n"
    )


async def run_chat() -> None:
    load_dotenv()

    # 2026 Google's best model but limited to 20 calls/day (according to Gemini, not able to confirm)
    model = "gemini-3-flash-preview"

    # Not as smart but get 1000 calls/day (same disclaimer) better for development 
    # model = "gemini-2.5-flash-lite"

    # The client will pick up GEMINI_API_KEY (or GOOGLE_API_KEY) from a .env file.
    # Create a (free) Gemini API key at https://aistudio.google.com/api-keys
    # You must add these lines to a new .env file with your API key:
    # GEMINI_API_KEY="YOUR_KEY_HERE"
    gemini = genai.Client()

    #
    def safe_generate(*, model, contents, config, retries=3, backoff_seconds=2):
        for attempt in range(retries):
            try:
                return gemini.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except errors.ServerError as e:
                # STUDENT NOTE:
                # The Gemini API sometimes returns 503 during spikes in demand.
                # This is not your fault. We retry a few times with backoff.
                msg = str(e)
                if "503" in msg or "UNAVAILABLE" in msg:
                    if attempt < retries - 1:
                        wait = backoff_seconds * (2 ** attempt)
                        print(f"\n[Gemini busy (503). Retrying in {wait}s...]")
                        time.sleep(wait)
                        continue
                raise  # other server errors or final attempt

    #____________________________

    # Launch the MCP server as a subprocess over stdio.
    async with Client("server.py") as mcp:
        # Discover capabilities
        mcp_tools = await mcp.list_tools()
        fn_decls = [_mcp_tool_to_function_declaration(t) for t in mcp_tools]
        tool = types.Tool(function_declarations=fn_decls)
        config = types.GenerateContentConfig(tools=[tool])

        # These are not used directly by Gemini function calling, but students need them.
        mcp_resources = await mcp.list_resources()
        mcp_prompts = await mcp.list_prompts()

        # Load skill context from SKILL.md files
        modules_dir = Path(__file__).parent / "modules"
        skill_context = _load_skill_context(modules_dir)

        system_capabilities_content = _capabilities_to_system_content(mcp_tools, mcp_resources, skill_context)

        print("\nConnected to MCP server.")
        print("Discovered tools:")
        for t in mcp_tools:
            print(f"  - {t.name}: {t.description}")

        print("\nDiscovered resources:")
        for r in mcp_resources:
            uri = getattr(r, "uri", None) or getattr(r, "name", None) or str(r)
            desc = getattr(r, "description", "") or ""
            print(f"  - {uri}" + (f": {desc}" if desc else ""))

        print("\nDiscovered prompts:")
        for p in mcp_prompts:
            name = getattr(p, "name", None) or str(p)
            desc = getattr(p, "description", "") or ""
            print(f"  - {name}" + (f": {desc}" if desc else ""))

        _print_help()
        print("\nType a request. Ctrl-C to quit.\n")

        while True:
            user_text = input("You: ").strip()
            if not user_text:
                continue

            if user_text.startswith("/"):
                parts = user_text.split(maxsplit=2)
                cmd = parts[0].lower()

                if cmd in {"/help", "/?"}:
                    _print_help()
                    continue

                if cmd == "/tools":
                    mcp_tools = await mcp.list_tools()
                    print("\nTools:")
                    for t in mcp_tools:
                        print(f"  - {t.name}: {t.description}")
                    print("")
                    continue

                if cmd == "/resources":
                    mcp_resources = await mcp.list_resources()
                    print("\nResources:")
                    for r in mcp_resources:
                        uri = getattr(r, "uri", None) or getattr(r, "name", None) or str(r)
                        desc = getattr(r, "description", "") or ""
                        print(f"  - {uri}" + (f": {desc}" if desc else ""))
                    print("")
                    continue

                if cmd == "/resource":
                    if len(parts) < 2:
                        print("\nUsage: /resource <uri>\n")
                        continue
                    uri = parts[1]
                    content_list = await mcp.read_resource(uri)
                    print(f"\nResource: {uri}")
                    for c in content_list:
                        txt = getattr(c, "text", None)
                        if txt is None:
                            txt = str(c)
                        print(txt)
                    print("")
                    continue

                if cmd == "/prompts":
                    mcp_prompts = await mcp.list_prompts()
                    print("\nPrompts:")
                    for p in mcp_prompts:
                        name = getattr(p, "name", None) or str(p)
                        desc = getattr(p, "description", "") or ""
                        print(f"  - {name}" + (f": {desc}" if desc else ""))
                    print("")
                    continue

                if cmd == "/prompt":
                    if len(parts) < 2:
                        print("\nUsage: /prompt <name> [json_args]\n")
                        continue
                    prompt_name = parts[1]
                    args: Dict[str, Any] = {}
                    if len(parts) == 3:
                        try:
                            args = json.loads(parts[2])
                        except json.JSONDecodeError as e:
                            print(f"\nCould not parse json_args: {e}\n")
                            continue

                    prompt_result = await mcp.get_prompt(prompt_name, args)
                    prompt_contents = _prompt_messages_to_gemini_contents(prompt_result)

                    if not prompt_contents:
                        print("\nPrompt rendered no messages.\n")
                        continue

                    # Send the rendered prompt messages to Gemini. Gemini may call tools.
                    response = safe_generate(
                        model=model,
                        contents=[system_capabilities_content, *prompt_contents],
                        config=config,
                    )

                    function_calls = response.function_calls or []
                    if not function_calls:
                        print(f"\nGemini: {response.text}\n")
                        continue
                    #_________________I removed this whole block
                    # Minimal: handle the first tool call only.############################
                    # fc = function_calls[0]
                    # tool_name = fc.name
                    # tool_args = dict(fc.args or {})

                    # print(f"\nGemini chose tool: {tool_name}")
                    # print("Args:")
                    # print(json.dumps(tool_args, indent=2))

                    # try:
                    #     tool_result = await mcp.call_tool(tool_name, tool_args)
                    #     result_data = getattr(tool_result, "data", tool_result)
                    #     function_response = {"result": result_data}
                    # except Exception as e:
                    #     function_response = {"error": str(e)}

                    # print("\nTool result:")
                    # print(function_response)

                    # function_call_content = response.candidates[0].content
                    # function_response_part = types.Part.from_function_response(
                    #     name=tool_name,
                    #     response=function_response,
                    # )
                    # function_response_content = types.Content(role="model", parts=[function_response_part])

                    # final = gemini.models.generate_content(
                    #     model=model,
                    #     contents=[
                    #         system_capabilities_content,
                    #         *prompt_contents,
                    #         function_call_content,
                    #         function_response_content,
                    #     ],
                    #     config=config,
                    # )
                    # print(f"\nGemini: {final.text}\n")
                    # continue
                    ###__________________


                    # Instead:

                    ### TOOL EXECUTION LOOP ###
                    # Allow the model to call tools multiple times in sequence.
                    # Loop until the model produces plain text output.

                    contents = [system_capabilities_content, *prompt_contents]
                    resp = response  # rename for clarity / consistency with the loop

                    while True:
                        function_calls = resp.function_calls or []
                        if not function_calls:
                            print(f"\nGemini: {resp.text}\n")
                            break

                        # Execute each tool call in order
                        for fc in function_calls:
                            tool_name = fc.name
                            tool_args = dict(fc.args or {})

                            print(f"\nGemini chose tool: {tool_name}")
                            print("Args:")
                            print(json.dumps(tool_args, indent=2))

                            try:
                                tool_result = await mcp.call_tool(tool_name, tool_args)
                                result_data = getattr(tool_result, "data", tool_result)
                                function_response = {"result": result_data}
                            except Exception as e:
                                function_response = {"error": str(e)}

                            print("\nTool result:")
                            print(function_response)

                            # IMPORTANT: include the model's function-call message AND our function-response message
                            function_call_content = resp.candidates[0].content
                            function_response_part = types.Part.from_function_response(
                                name=tool_name,
                                response=function_response,
                            )
                            function_response_content = types.Content(role="model", parts=[function_response_part])

                            contents.extend([function_call_content, function_response_content])

                            # Ask Gemini again, now that it has the tool result
                            resp = safe_generate(
                                model=model,
                                contents=contents,
                                config=config,
                            )

                    continue



                print("\nUnknown command. Type /help\n")
                continue

            # Normal free-form turn: ask Gemini what tool to call (if any)
            user_prompt_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_text)],
            )
            response = safe_generate(
                model=model,
                contents=[system_capabilities_content, user_prompt_content],
                config=config,
            )

            function_calls = response.function_calls or []
            if not function_calls:
                print(f"\nGemini: {response.text}\n")
                continue


#same for this part:
            # fc = function_calls[0]
            # tool_name = fc.name
            # tool_args = dict(fc.args or {})

            # print(f"\nGemini chose tool: {tool_name}")
            # print("Args:")
            # print(json.dumps(tool_args, indent=2))

            # try:
            #     tool_result = await mcp.call_tool(tool_name, tool_args)
            #     result_data = getattr(tool_result, "data", tool_result)
            #     function_response = {"result": result_data}
            # except Exception as e:
            #     function_response = {"error": str(e)}

            # print("\nTool result:")
            # print(function_response)

            # function_call_content = response.candidates[0].content
            # function_response_part = types.Part.from_function_response(
            #     name=tool_name,
            #     response=function_response,
            # )
            # function_response_content = types.Content(role="model", parts=[function_response_part])

            # final = gemini.models.generate_content(
            #     model=model,
            #     contents=[
            #         system_capabilities_content,
            #         user_prompt_content,
            #         function_call_content,
            #         function_response_content,
            #     ],
            #     config=config,
            # )
            # print(f"\nGemini: {final.text}\n")
            
            #_________________________
            ### TOOL EXECUTION LOOP ###
            # Allow the model to call tools multiple times in sequence.
            # Loop until the model produces plain text output.

            contents = [system_capabilities_content, user_prompt_content]
            resp = response

            while True:
                function_calls = resp.function_calls or []
                if not function_calls:
                    print(f"\nGemini: {resp.text}\n")
                    break

                for fc in function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args or {})

                    print(f"\nGemini chose tool: {tool_name}")
                    print("Args:")
                    print(json.dumps(tool_args, indent=2))

                    try:
                        tool_result = await mcp.call_tool(tool_name, tool_args)
                        result_data = getattr(tool_result, "data", tool_result)
                        function_response = {"result": result_data}
                    except Exception as e:
                        function_response = {"error": str(e)}

                    print("\nTool result:")
                    print(function_response)

                    function_call_content = resp.candidates[0].content
                    function_response_part = types.Part.from_function_response(
                        name=tool_name,
                        response=function_response,
                    )
                    function_response_content = types.Content(role="model", parts=[function_response_part])

                    contents.extend([function_call_content, function_response_content])

                    resp = safe_generate(
                        model=model,
                        contents=contents,
                        config=config,
                    )


if __name__ == "__main__":
    asyncio.run(run_chat())
