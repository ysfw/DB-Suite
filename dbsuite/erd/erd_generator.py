import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError
if __package__:
    from .models.ER import ERSchema
else:
    from models.ER import ERSchema

load_dotenv()

def generate_erd(description: str, retries: int = 3) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=api_key)

    prompt = f"""You are a database design specialist.
Design a standard Entity-Relationship Diagram (ERD) based on the user's description.

STRICT ERD RULES:
1. Use standard ERD only. Do NOT use EERD (no inheritance, specialization, generalization, superclasses, or subclasses).
2. Entities:
   - Strong entities: 'isWeak' is false, 'partialKey' must be null. Must have at least one primary key ('isPrimaryKey': true).
   - Weak entities: 'isWeak' is true, 'partialKey' must be a non-empty list of attribute names that form its partial key.
   - Attributes: can be multi-valued ('isMultiValued': true), derived ('isDerived': true), or composite.
   - A 'composite' list can contain simple component-name strings or attribute objects with their own flags and nested 'composite' lists. Preserve all levels of nesting.
3. Relationships:
   - Identifying relationships: 'isIdentifying' is true and must connect at least 2 entities (owner and weak entity).
   - Participant entities: specify 'entityName', 'cardinality' ('1', 'N', 'M'), and 'participation' ('total' or 'partial').
   - Relationships may have their own 'attributes' list, using the same attribute structure (including derived, multivalued, and nested composite attributes) as entity attributes.

Description:
{description}
"""

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": ERSchema.model_json_schema(),
                },
            )
            return response.text
        except ServerError as err:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise err
