from fastapi import FastAPI
from pydantic import BaseModel
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os
import re  # for cleaning regex

# Load .env file
load_dotenv()

# API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found! Add it to your .env file.")

# LLM Config
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=GEMINI_API_KEY,
    temperature=0.3
)

# FastAPI App
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Model
class FinanceInput(BaseModel):
    income: float
    expenses: dict
    savings_goal: float = 0
    debt: float = 0
    risk_level: str = "medium"


@app.get("/")
def home():
    return {"message": "AI Personal Finance Advisor API is running 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/plan")
def generate_plan(data: FinanceInput):

    # Shared context for both agents
    context = (
        f"Income: {data.income}\n"
        f"Expenses: {data.expenses}\n"
        f"Savings Goal: {data.savings_goal}\n"
        f"Debt: {data.debt}\n"
        f"Risk Level: {data.risk_level}\n"
    )

    # ---------------------------------------------------
    # AGENTS (GLOBAL, GENERAL)
    # ---------------------------------------------------

    budget_agent = Agent(
        role="Global Budgeting Expert",
        goal=(
            "Create a clear, simple monthly budget using universal categories and "
            "financial best practices. Output must be clean Markdown."
        ),
        backstory=(
            "You are a professional financial planner helping clients worldwide. "
            "You follow global budgeting standards such as the 50/30/20 rule, "
            "expense categorization, surplus calculation, and savings strategy. "
            "Your tone is friendly, simple, and beginner-friendly."
        ),
        llm=gemini_llm,
        verbose=True  # logs in console only
    )

    investment_agent = Agent(
        role="Global Investment Advisor",
        goal=(
            "Create a simple long-term investment plan using global investment "
            "principles: index funds, ETFs, bonds, diversification, and risk-based "
            "allocation. Output must be clean Markdown."
        ),
        backstory=(
            "You specialize in low-cost investing using global diversified index funds, "
            "bond funds, cash reserves, ETFs, and basic portfolio allocation. "
            "Advice must be beginner-friendly and long-term focused."
        ),
        llm=gemini_llm,
        verbose=True  # logs in console only
    )

    # ---------------------------------------------------
    # TASKS
    # ---------------------------------------------------

    task1 = Task(
        description=(
            context +
            "\n\nCreate a clean Markdown monthly budget.\n"
            "MUST INCLUDE:\n"
            "1. Table: Income, Total Expenses, Surplus/Deficit\n"
            "2. Needs / Wants / Savings (50-30-20 rule table)\n"
            "3. Expense Breakdown Table (each expense individually)\n"
            "4. Savings & Debt Strategy (short bullets)\n"
            "5. Monthly action steps (around 5–7 bullet points)\n\n"
            "RULES:\n"
            "- Use Markdown tables where requested\n"
            "- No backticks, no code blocks\n"
            "- Keep explanations short and simple\n"
        ),
        expected_output="Markdown formatted global budget plan.",
        agent=budget_agent
    )

    task2 = Task(
    description=(
        context +
        "\n\nCreate a clean Markdown long-term investment plan.\n"
        "You MUST adjust the asset allocation based on risk:\n"
        "LOW RISK:\n"
        "  Equity 20–40%, Bonds 50–70%, Cash 10–20%\n"
        "MEDIUM RISK:\n"
        "  Equity 50–70%, Bonds 20–40%, Cash 5–10%\n"
        "HIGH RISK:\n"
        "  Equity 70–90%, Bonds 10–20%, Cash 0–10%\n\n"
        "MUST INCLUDE:\n"
        "1. Short risk profile explanation\n"
        "2. Markdown asset allocation table:\n"
        "   | Asset Class | Allocation | Description |\n"
        "3. Recommended investment types (global index funds, bond funds, cash)\n"
        "4. Monthly investment breakdown table based on the user's surplus:\n"
        "   | Investment Type | Allocation | Monthly Amount |\n"
        "5. Beginner tips (5 bullets)\n\n"
        "RULES:\n"
        "- Use Markdown tables\n"
        "- NO backticks, NO code blocks\n"
        "- Simple English explanations"
    ),
    expected_output="Markdown formatted global investment plan.",
    agent=investment_agent
)


    # ---------------------------------------------------
    # CREW
    # ---------------------------------------------------
    crew = Crew(
        agents=[budget_agent, investment_agent],
        tasks=[task1, task2],
        verbose=False  # crew-level logs minimal
    )

    result = crew.kickoff()

    # ---------------------------------------------------
    # Helper: safely extract text from TaskOutput across versions
    # ---------------------------------------------------
    def task_output_to_text(task_output) -> str:
        """
        Try several common attributes used in different CrewAI versions.
        Fallback to str(task_output) if nothing else works.
        """
        for attr in ("output_text", "final_output", "raw", "result", "completion"):
            val = getattr(task_output, attr, None)
            if isinstance(val, str) and val.strip():
                return val
        return str(task_output)

    # ---------------------------------------------------
    # Extract raw outputs from tasks
    # ---------------------------------------------------
    try:
        t1_raw = task_output_to_text(result.tasks_output[0])
        t2_raw = task_output_to_text(result.tasks_output[1])
    except Exception:
        # Fallback: if tasks_output behaves differently, use overall result
        t1_raw = ""
        t2_raw = str(result)

    # ---------------------------------------------------
    # CLEANING FUNCTION (your clean(text) included)
    # ---------------------------------------------------
    def clean(text: str) -> str:
        if not text:
            return ""
        remove_list = [
            "╭", "╰", "│", "─",
            "Crew Execution Started", "Final Answer:", "Agent:", "Task:",
            "Name:", "ID:", "Tool Args:", "Crew:",
            "```markdown", "```", "`", "None"
        ]
        for r in remove_list:
            text = text.replace(r, "")

        # remove 'markdown' when it's alone on a line
        text = re.sub(r"(?im)^\s*markdown\s*$", "", text)

        # strip empty lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)

    # Clean both outputs
    task1_output = clean(t1_raw)
    task2_output = clean(t2_raw)

    # ---------------------------------------------------
    # Combine final Markdown for frontend
    # ---------------------------------------------------
    final_markdown = f"""
## 🧾 Monthly Budget Plan
{task1_output}

---

## 📈 Investment Plan
{task2_output}
""".strip()

    return {
        "advice": final_markdown,
        "raw_expenses": data.expenses
    }
