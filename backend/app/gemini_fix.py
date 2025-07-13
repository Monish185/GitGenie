import os
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
fix_cache: dict[tuple[str, str, int], str] = {}
client = genai.Client()


# ---------- helpers --------------------------------------------------------- #
def _extract_text(blob) -> str:
    """
    Turn a Gemini Content/Part (or plain str) into pure text.
    """
    if isinstance(blob, str):
        return blob

    # Gemini ≥ v1 – .text field is present
    if hasattr(blob, "text") and isinstance(blob.text, str):
        return blob.text

    # Gemini beta – .parts is a list of Part objects
    if hasattr(blob, "parts"):
        return "".join(
            p.text if hasattr(p, "text") else str(p)         # join all parts
            for p in blob.parts
        )

    # Fallback – string‑ify whatever it is
    return str(blob)


def clean_markdown(raw: str) -> str:
    """Strip ``` fences and leading/trailing whitespace."""
    return (
        raw.replace("```python", "")
           .replace("```", "")
           .strip()
    )


# ---------- main entry ------------------------------------------------------ #
def fix_code_with_gemini(
    file_path: str,
    smell_code: str,
    line_number: int,
    save: bool = True,
) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY env-var is missing")

    # Cache-hit
    cache_key = (file_path, smell_code, line_number)
    if cache_key in fix_cache:
        return fix_cache[cache_key]

    # 1. read file ----------------------------------------------------------- #
    with open(file_path, "r") as fh:
        content = fh.read()

    # 2. craft prompt -------------------------------------------------------- #
    match smell_code:
        case "C0114":
            prompt = (
                "Add a one-liner *module* docstring at the very top.\n\n"
                f'File content:\n"""{content}"""'
            )
        case "C0115":
            prompt = (
                "Add a one-liner *class* docstring.\n\n"
                f'File content:\n"""{content}"""'
            )
        case "C0301":
            prompt = (
                "Refactor any line >100 chars so it complies with PEP-8.\n\n"
                f'File content:\n"""{content}"""'
            )
        case "C0303":
            prompt = (
                "Refactor overly complex lines into simpler constructs.\n\n"
                f'File content:\n"""{content}"""'
            )
        case "C0411":
            prompt = (
                "Move all import statements to the top of the file (PEP-8).\n\n"
                f'File content:\n"""{content}"""'
            )
        case "C0412":
            prompt = (
                "Replace the wildcard import with explicit names.\n\n"
                f'File content:\n"""{content}"""'
            )
        case _ if smell_code.startswith("C041") or smell_code == "E0401":
            prompt = (
                "Remove or fix any unused / unresolved imports.\n\n"
                f'File content:\n"""{content}"""'
            )
        case _ if smell_code.startswith("E11"):
            prompt = (
                f"Fix the {smell_code} attribute / call error shown below.\n\n"
                f'File content:\n"""{content}"""'
            )
        case "D0123":
            prompt = (
                "Re-format all docstrings to follow PEP-257.\n\n"
                f'File content:\n"""{content}"""'
            )
        case _:
            raise ValueError(f"Unsupported smell code → {smell_code}")

    # 3. call Gemini --------------------------------------------------------- #
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw_reply = resp.candidates[0].content            # Content object
    fixed_code = clean_markdown(_extract_text(raw_reply))

    if not fixed_code:
        raise RuntimeError("Gemini returned empty fix")

    # 4. persist if requested ------------------------------------------------ #
    if save:
        with open(file_path, "w") as fh:
            fh.write(fixed_code)
        print(f"✅Fix written to {file_path}")
    else:
        print(f"👁Preview only for {file_path}")

    fix_cache[cache_key] = fixed_code
    return fixed_code
