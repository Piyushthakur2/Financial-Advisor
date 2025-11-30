document.getElementById("financeForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const income = document.getElementById("income").value;
    const expenses = document.getElementById("expenses").value;
    const savings_goal = document.getElementById("savings_goal").value;
    const debt = document.getElementById("debt").value;
    const risk = document.getElementById("risk").value;

    // Convert expenses string → object
    const expenseObj = {};
    expenses.split(",").forEach(pair => {
        const [key, val] = pair.split(":").map(s => s.trim());
        if (key && val) expenseObj[key] = Number(val);
    });

    const outputDiv = document.getElementById("output");
    outputDiv.innerHTML = "<p><b>Generating plan… Please wait...</b></p>";

    const API_URL = window.BACKEND_URL + "/plan";

    try {
        const res = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                income: Number(income),
                expenses: expenseObj,
                savings_goal: Number(savings_goal),
                debt: Number(debt),
                risk_level: risk
            })
        });

        const data = await res.json();
        processMarkdownAndDisplay(data);

    } catch (error) {
        outputDiv.innerHTML = `<p style="color:red;">❌ Network Error: ${error}</p>`;
    }
});

// MARKDOWN PROCESSOR
function processMarkdownAndDisplay(data) {
    const outputDiv = document.getElementById("output");

    if (!data) {
        outputDiv.innerHTML = `<p style="color:red;">❌ No response from server.</p>`;
        return;
    }

    let text = "";

    if (data.advice) text = data.advice;
    else if (data.final_output) text = data.final_output;
    else if (typeof data === "string") text = data;
    else text = "```\n" + JSON.stringify(data, null, 2) + "\n```";

    outputDiv.innerHTML = marked.parse(text);
}
