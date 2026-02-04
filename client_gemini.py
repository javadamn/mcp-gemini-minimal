from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
from io import StringIO
from Bio import SeqIO
def _strip_ctx_from_schema(schema: dict) -> dict:
    schema = dict(schema or {})
    props = dict(schema.get("properties", {}))
    props.pop("ctx", None)
    schema["properties"] = props

    if "required" in schema:
        schema["required"] = [r for r in schema["required"] if r != "ctx"]

    return schema

from dotenv import load_dotenv
from fastmcp import Client
from google import genai
from google.genai import types

def _capabilities_to_system_content(mcp_tools, mcp_resources) -> types.Content:
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

        resources_json.append({
            "uri": uri_str,
            "description": getattr(r, "description", ""),
        })

    payload = {
        "mcp_tools": tools_json,
        "mcp_resources": resources_json,
        "instruction": (
            "You may call MCP tools using their schemas. "
            "If a user refers to a plasmid, file, or dataset, "
            "select the appropriate resource URI from mcp_resources. "
            "The client will resolve resources into sequences before calling tools."
        ),
    }
    return types.Content(
        role="model",
        parts=[types.Part.from_text(
            text="SYSTEM CONTEXT (capabilities, not user input):\n" + json.dumps(payload, indent=2)
        )],
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

async def _genbank_resource_to_sequence(mcp: Client, uri: str) -> str:
    """Client-side adapter: read a GenBank MCP resource and return its DNA sequence."""
    parts = await mcp.read_resource(uri)

    text_chunks = []
    for p in parts:
        if hasattr(p, "text") and p.text is not None:
            text_chunks.append(p.text)
        elif hasattr(p, "blob") and p.blob is not None:
            text_chunks.append(p.blob.decode("utf-8"))

    if not text_chunks:
        raise ValueError(f"Resource {uri} did not contain readable GenBank data.")

    text = "\n".join(text_chunks)
    record = SeqIO.read(StringIO(text), "genbank")

    if not record.seq:
        raise ValueError(f"GenBank record in {uri} contains no sequence.")

    return str(record.seq)


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
    # Create a (free) Gemini API key at https://ai.google.dev/gemini-api/docs/pricing?utm_source=chatgpt.com
    # You must add these lines to a new .env file with your API key:
    # GEMINI_API_KEY="YOUR_KEY_HERE"
    gemini = genai.Client()

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

        system_capabilities_content = _capabilities_to_system_content(mcp_tools, mcp_resources)

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
                    response = gemini.models.generate_content(
                        model=model,
                        contents=[system_capabilities_content, *prompt_contents],
                        config=config,
                    )

                    function_calls = response.function_calls or []
                    if not function_calls:
                        print(f"\nGemini: {response.text}\n")
                        continue

                    # Minimal: handle the first tool call only.
                    fc = function_calls[0]
                    tool_name = fc.name
                    tool_args = dict(fc.args or {})

                    # Option A: client resolves GenBank resources to sequences
                    if "uri" in tool_args:
                        seq = await _genbank_resource_to_sequence(mcp, tool_args["uri"])
                        tool_args = {"sequence": seq}

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

                    function_call_content = response.candidates[0].content
                    function_response_part = types.Part.from_function_response(
                        name=tool_name,
                        response=function_response,
                    )
                    function_response_content = types.Content(role="model", parts=[function_response_part])

                    final = gemini.models.generate_content(
                        model=model,
                        contents=[
                            system_capabilities_content,
                            *prompt_contents,
                            function_call_content,
                            function_response_content,
                        ],
                        config=config,
                    )
                    print(f"\nGemini: {final.text}\n")
                    continue

                print("\nUnknown command. Type /help\n")
                continue

            # Normal free-form turn: ask Gemini what tool to call (if any)
            user_prompt_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_text)],
            )
            response = gemini.models.generate_content(
                model=model,
                contents=[system_capabilities_content, user_prompt_content],
                config=config,
            )

            function_calls = response.function_calls or []
            if not function_calls:
                print(f"\nGemini: {response.text}\n")
                continue

            fc = function_calls[0]
            tool_name = fc.name
            tool_args = dict(fc.args or {})

            # Option A: client resolves GenBank resources to sequences
            if "uri" in tool_args:
                seq = await _genbank_resource_to_sequence(mcp, tool_args["uri"])
                tool_args = {"sequence": seq}

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

            function_call_content = response.candidates[0].content
            function_response_part = types.Part.from_function_response(
                name=tool_name,
                response=function_response,
            )
            function_response_content = types.Content(role="model", parts=[function_response_part])

            final = gemini.models.generate_content(
                model=model,
                contents=[
                    system_capabilities_content,
                    user_prompt_content,
                    function_call_content,
                    function_response_content,
                ],
                config=config,
            )
            print(f"\nGemini: {final.text}\n")


if __name__ == "__main__":
    asyncio.run(run_chat())
