from fastapi import FastAPI
from pydantic import BaseModel
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

# Load .env file
load_dotenv()


# Single API key (simple setup)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found! Add it to your .env file.")

# Configure Gemini LLM
gemini_llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=GEMINI_API_KEY,
    temperature=0.3
)

# FastAPI app
app = FastAPI()

# Enable CORS (local + render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
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

    context = (
        f"User Income: {data.income}\n"
        f"Expenses: {data.expenses}\n"
        f"Savings Goal: {data.savings_goal}\n"
        f"Debt: {data.debt}\n"
        f"Risk Level: {data.risk_level}\n"
    )

    # ---------- 2 Agents ----------
    # Agent 1: Budget + Savings
    budget_agent = Agent(
        role="Budget & Savings Analyst",
        goal="Create the monthly budget and savings/debt strategy.",
        backstory="Expert in budgeting, financial planning & savings structure.",
        llm=gemini_llm,
        verbose=True
    )

    # Agent 2: Investment Advisor
    investment_agent = Agent(
        role="Investment Advisor",
        goal="Recommend investments based on risk level.",
        backstory="Expert in low-risk and medium-risk investment strategies.",
        llm=gemini_llm,
        verbose=True
    )

    # ---------- Tasks ----------
    task1 = Task(
        description=(
            context +
            "\nTask: Create a clear monthly budget summary using markdown. "
            "Include Needs/Wants/Savings percentages, surplus, debt payoff strategy, "
            "and emergency fund plan. Use tables."
        ),
        expected_output="Markdown budget + savings plan.",
        agent=budget_agent
    )

    task2 = Task(
        description=(
            context +
            "\nTask: Suggest a simple monthly investment plan based on risk profile. "
            "Include asset allocation and example index funds/ETFs."
        ),
        expected_output="Markdown investment strategy.",
        agent=investment_agent
    )

    # ---------- Crew ----------
    crew = Crew(
        agents=[budget_agent, investment_agent],
        tasks=[task1, task2],
        verbose=True
    )

    result = crew.kickoff()
    final_text = str(result)

    return {
        "advice": final_text,
        "budget_plan": data.expenses  # keeps your frontend working
    }
