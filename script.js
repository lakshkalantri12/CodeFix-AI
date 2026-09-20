const API_URL = "https://codefix-ai-1.onrender.com/analyze";

const languageSelect = document.getElementById("languageSelect");
const codeInput = document.getElementById("codeInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const errorOutput = document.getElementById("errorOutput");
const fixedCode = document.getElementById("fixedCode");
const copyBtn = document.getElementById("copyBtn");
const clearBtn = document.getElementById("clearBtn");
const issueBadge = document.getElementById("issueBadge");
const lineCount = document.getElementById("lineCount");
const charCount = document.getElementById("charCount");
const startBtn = document.getElementById("startBtn");
const navCodeFix = document.getElementById("navCodeFix");
const backHomeBtn = document.getElementById("backHomeBtn");


function openEditor() {
    document.getElementById("editor").scrollIntoView({ behavior: "smooth" });
    navCodeFix.classList.add("active");
}

function goHome() {
    document.getElementById("home").scrollIntoView({ behavior: "smooth" });
}

startBtn.addEventListener("click", openEditor);
navCodeFix.addEventListener("click", () => setTimeout(() => navCodeFix.classList.add("active"), 50));
backHomeBtn.addEventListener("click", goHome);

function updateCounts() {
    const lines = codeInput.value ? codeInput.value.split("\n").length : 1;
    const chars = codeInput.value.length;
    lineCount.textContent = `${lines} ${lines === 1 ? "line" : "lines"}`;
    charCount.textContent = `${chars} ${chars === 1 ? "character" : "characters"}`;
}

function escapeHTML(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderErrors(errors) {
    issueBadge.textContent = `${errors.length} ${errors.length === 1 ? "issue" : "issues"}`;
    if (!errors.length) {
        errorOutput.innerHTML = `<div class="success">✓ No common issues found!</div>`;
        return;
    }

    errorOutput.innerHTML = errors.map((err, index) => `
        <div class="error-item">
            <div class="error-title">⚠️ ${index + 1}. ${escapeHTML(err.message)}</div>
            <div class="error-line"><strong>Line ${escapeHTML(err.line)}</strong></div>
            <div class="error-why"><strong>Why:</strong> ${escapeHTML(err.why)}</div>
            <div class="error-fix"><strong>Fix:</strong> ${escapeHTML(err.fix)}</div>
        </div>
    `).join("");
}

analyzeBtn.addEventListener("click", async () => {
    analyzeBtn.disabled = true;
    analyzeBtn.querySelector("span").textContent = "Analyzing...";
    errorOutput.innerHTML = `<div class="empty-state">Checking your code...</div>`;

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: codeInput.value,
                language: languageSelect.value
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data?.errors?.[0]?.message || "Analysis failed");

        renderErrors(data.errors || []);
        fixedCode.textContent = data.fixed_code || codeInput.value;
    } catch (error) {
        issueBadge.textContent = "Connection error";
        errorOutput.innerHTML = `<div class="error-item"><div class="error-title">⚠️ Backend connection failed</div><div class="error-why">Make sure <strong>python app.py</strong> is running in PowerShell.</div></div>`;
        fixedCode.textContent = "";
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.querySelector("span").textContent = "Analyze Code";
    }
});

copyBtn.addEventListener("click", async () => {
    const text = fixedCode.textContent;
    if (!text || text === "Fixed code will appear here.") return;
    try {
        await navigator.clipboard.writeText(text);
        copyBtn.textContent = "Copied!";
        setTimeout(() => copyBtn.textContent = "Copy Code", 1200);
    } catch {
        copyBtn.textContent = "Copy failed";
        setTimeout(() => copyBtn.textContent = "Copy Code", 1200);
    }
});

clearBtn.addEventListener("click", () => {
    codeInput.value = "";
    fixedCode.textContent = "Fixed code will appear here.";
    issueBadge.textContent = "0 issues";
    errorOutput.innerHTML = `<div class="empty-state">Run Analyze Code to check your program.</div>`;
    updateCounts();
});


languageSelect.addEventListener("change", () => {
    fixedCode.textContent = "Fixed code will appear here.";
    issueBadge.textContent = "0 issues";
    errorOutput.innerHTML = `<div class="empty-state">Language changed to ${escapeHTML(languageSelect.value)}. Enter your code and click Analyze Code.</div>`;
});

codeInput.addEventListener("input", updateCounts);
updateCounts();
