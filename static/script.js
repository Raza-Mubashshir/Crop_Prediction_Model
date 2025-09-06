function displayPredictions(predictions) {
    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = "";

    // Create tabs for yearly and monthly views
    const tabsDiv = document.createElement("div");
    tabsDiv.className = "prediction-tabs";
    tabsDiv.innerHTML = `
        <button class="tab-button active" onclick="switchTab(event, 'yearly')">Yearly View</button>
        <button class="tab-button" onclick="switchTab(event, 'monthly')">Monthly View</button>
    `;
    resultsDiv.appendChild(tabsDiv);

    // Create container for yearly predictions
    const yearlyDiv = document.createElement("div");
    yearlyDiv.id = "yearly-predictions";
    yearlyDiv.className = "prediction-content active";
    
    // Create yearly predictions table
    const yearlyTable = document.createElement("table");
    yearlyTable.className = "prediction-table";
    yearlyTable.innerHTML = `
        <thead>
            <tr>
                <th>Year</th>
                <th>Average Predicted Price (₹)</th>
            </tr>
        </thead>
        <tbody>
            ${predictions.yearly_predictions.map(pred => `
                <tr>
                    <td>${new Date(pred.date).getFullYear()}</td>
                    <td>₹${pred.price.toFixed(2)}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    yearlyDiv.appendChild(yearlyTable);
    resultsDiv.appendChild(yearlyDiv);

    // Create container for monthly predictions
    const monthlyDiv = document.createElement("div");
    monthlyDiv.id = "monthly-predictions";
    monthlyDiv.className = "prediction-content";
    
    // Group monthly predictions by year
    const monthlyByYear = {};
    predictions.monthly_predictions.forEach(pred => {
        const date = new Date(pred.date);
        const year = date.getFullYear();
        if (!monthlyByYear[year]) {
            monthlyByYear[year] = [];
        }
        monthlyByYear[year].push({
            month: date.toLocaleString('default', { month: 'long' }),
            price: pred.price
        });
    });

    // Create tables for each year's monthly predictions
    for (const year in monthlyByYear) {
        const yearHeader = document.createElement("h3");
        yearHeader.textContent = `Year ${year}`;
        monthlyDiv.appendChild(yearHeader);

        const table = document.createElement("table");
        table.className = "prediction-table";
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Month</th>
                    <th>Predicted Price (₹)</th>
                </tr>
            </thead>
            <tbody>
                ${monthlyByYear[year].map(pred => `
                    <tr>
                        <td>${pred.month}</td>
                        <td>₹${pred.price.toFixed(2)}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        monthlyDiv.appendChild(table);
    }
    resultsDiv.appendChild(monthlyDiv);
}

// Function to switch between yearly and monthly views
function switchTab(event, tabName) {
    const tabButtons = document.getElementsByClassName("tab-button");
    const tabContents = document.getElementsByClassName("prediction-content");

    // Remove active class from all buttons and contents
    Array.from(tabButtons).forEach(button => button.classList.remove("active"));
    Array.from(tabContents).forEach(content => content.classList.remove("active"));

    // Add active class to clicked button and corresponding content
    event.currentTarget.classList.add("active");
    document.getElementById(`${tabName}-predictions`).classList.add("active");
} 