from fastapi import FastAPI
from pydantic import BaseModel
from crewai import Agent, Task, Crew, LLM
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Read Gemini API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY is None:
    raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")

# Configure Gemini LLM for CrewAI
gemini_llm = LLM(
    model="gemini/gemini-2.5-pro",  # Use your Gemini model
    api_key=GEMINI_API_KEY,
    temperature=0.3,  # Slight creativity
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow ALL frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Basic Routes ----------
@app.get("/")
def read_root():
    return {"message": "AI Personal Finance Advisor API is running 🚀"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# ---------- Request Model ----------
class FinanceInput(BaseModel):
    income: float
    expenses: dict
    savings_goal: float = 0
    debt: float = 0
    risk_level: str = "medium"

# ---------- Agentic AI: Finance Advisor ----------
@app.post("/plan")
def generate_budget(data: FinanceInput):
    """Use CrewAI Agent + Gemini to create a personalized budget plan"""

    # 1. Define the Finance Advisor agent
    finance_agent = Agent(
        role="Personal Finance Advisor",
        goal="Analyze user's income, expenses, savings goal, debt, and risk level. "
             "Provide a clear, actionable monthly budget plan and suggestions for saving or investing.",
        backstory=(
            "You are a highly skilled financial advisor. "
            "You know how to create personalized budget plans for individuals "
            "considering their income, expenses, debts, savings goals, and risk preference."
        ),
        llm=gemini_llm,
        verbose=True,
    )

    # 2. Define the task for this agent
    task_description = (
        f"User Income: {data.income}\n"
        f"Expenses: {data.expenses}\n"
        f"Savings Goal: {data.savings_goal}\n"
        f"Debt: {data.debt}\n"
        f"Risk Level: {data.risk_level}\n\n"
        "Please provide a detailed monthly budget plan. "
        "Include: suggested allocation for each expense category, "
        "recommended savings amount, and advice for debt repayment or investments."
    )

    finance_task = Task(
        description=task_description,
        expected_output="A clear, actionable budget plan with advice for saving and investing.",
        agent=finance_agent,
    )

    # 3. Create a crew with this single agent
    crew = Crew(
        agents=[finance_agent],
        tasks=[finance_task],
        verbose=True,
    )

    # 4. Run the crew
    result = crew.kickoff()

    # 5. Return result to frontend
    return {
        "budget_plan": data.expenses,  # keep original expenses for reference
        "advice": str(result)
    }
