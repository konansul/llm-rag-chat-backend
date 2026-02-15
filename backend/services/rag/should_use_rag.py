def should_use_rag(client, question:str, documents: list[dict]) -> bool:
    if not documents:
        return False

    docs_list = "\n".join(
        f"- {doc['title']}"
        for doc in documents
    )

    prompt = f"""
    You are a routing agent.

    User question:
    "{question}"

    User has uploaded the following documents:
    {docs_list}

    If the question is clearly related to one of these documents,
    answer ONLY with YES.

    If the question is general knowledge or unrelated,
    answer ONLY with NO.

    Do not explain.
    Respond with exactly YES or NO.
    """

    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = prompt,
    )

    decision = (response.text or "").strip().upper()

    return decision == "YES"
