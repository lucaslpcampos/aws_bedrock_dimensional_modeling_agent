"""
demo_chat.py
============
Interactive CLI to test the Dimensional Modeling RAG Agent.

Maintains session state across turns for multi-turn conversation.
Displays retrieved KB chunks when --trace is enabled.

Usage:
    python scripts/demo_chat.py [--profile PROFILE] [--trace]

Commands during chat:
    /quit  — exit the chat
    /new   — start a new session (clears conversation history)
    /kb    — query the knowledge base directly (bypasses agent)
"""
import argparse
import sys
import uuid
import boto3
from botocore.exceptions import ClientError


def get_stack_output(cf_client, stack_name: str, output_key: str) -> str:
    response = cf_client.describe_stacks(StackName=stack_name)
    outputs = response["Stacks"][0].get("Outputs", [])
    for output in outputs:
        if output["OutputKey"] == output_key:
            return output["OutputValue"]
    raise ValueError(f"Output '{output_key}' not found in stack '{stack_name}'")


def invoke_agent(client, agent_id: str, alias_id: str, session_id: str,
                 message: str, enable_trace: bool) -> tuple[str, list]:
    """Invoke the Bedrock Agent and collect the streaming response."""
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=message,
        enableTrace=enable_trace,
    )

    full_response = ""
    citations = []

    for event in response["completion"]:
        if "chunk" in event:
            chunk = event["chunk"]
            if "bytes" in chunk:
                full_response += chunk["bytes"].decode("utf-8")
            if "attribution" in chunk:
                for citation in chunk["attribution"].get("citations", []):
                    for ref in citation.get("retrievedReferences", []):
                        citations.append(ref)

        if enable_trace and "trace" in event:
            trace = event["trace"].get("trace", {})
            # Show retrieval trace (which KB chunks were used)
            kb_lookup = (
                trace.get("orchestrationTrace", {})
                .get("observation", {})
                .get("knowledgeBaseLookupOutput", {})
            )
            if kb_lookup:
                for result in kb_lookup.get("retrievedReferences", []):
                    score = result.get("score", 0)
                    content = result.get("content", {}).get("text", "")[:200]
                    print(f"\n  [KB chunk, score={score:.3f}] {content}...")

    return full_response, citations


def query_kb_directly(client, kb_id: str, query: str, n_results: int = 5) -> None:
    """Query the KB directly without going through the agent."""
    response = client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": n_results}
        },
    )
    print(f"\nTop {n_results} KB results for: '{query}'\n")
    for i, result in enumerate(response["retrievalResults"], 1):
        score = result.get("score", 0)
        content = result["content"]["text"]
        print(f"[{i}] Score: {score:.4f}")
        print(f"    {content[:400]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Chat with the Dimensional Modeling Agent")
    parser.add_argument("--profile", default=None, help="AWS profile name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--trace", action="store_true", help="Show retrieved KB chunks")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    cf = session.client("cloudformation")
    bedrock_agent_rt = session.client("bedrock-agent-runtime")

    print("Fetching agent configuration from CloudFormation...")
    try:
        agent_id = get_stack_output(cf, "DimModelingAgent", "AgentId")
        agent_alias_id = get_stack_output(cf, "DimModelingAgent", "AgentAliasId")
        kb_id = get_stack_output(cf, "DimModelingKB", "KnowledgeBaseId")
    except Exception as e:
        print(f"ERROR: {e}")
        print("Make sure all three CDK stacks are deployed.")
        sys.exit(1)

    session_id = str(uuid.uuid4())
    print(f"\nDimensional Modeling Agent")
    print(f"Agent ID  : {agent_id}")
    print(f"Session   : {session_id}")
    print(f"Trace     : {'ON' if args.trace else 'OFF (use --trace to enable)'}")
    print("-" * 60)
    print("Commands: /quit  /new  /kb <query>")
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("Goodbye!")
            break

        if user_input == "/new":
            session_id = str(uuid.uuid4())
            print(f"New session started: {session_id}")
            continue

        if user_input.startswith("/kb "):
            query_kb_directly(bedrock_agent_rt, kb_id, user_input[4:].strip())
            continue

        try:
            print("\nAgent: ", end="", flush=True)
            response_text, citations = invoke_agent(
                bedrock_agent_rt,
                agent_id,
                agent_alias_id,
                session_id,
                user_input,
                args.trace,
            )
            print(response_text)

            if citations and not args.trace:
                print(f"\n  [{len(citations)} source(s) from knowledge base]")

        except ClientError as e:
            print(f"\nERROR calling Bedrock Agent: {e}")


if __name__ == "__main__":
    main()
