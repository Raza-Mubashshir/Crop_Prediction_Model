import matplotlib.pyplot as plt
import numpy as np

# Data
commodities = ["Rice", "Wheat", "Maize", "Barley", "Soybean", "Groundnut", "Sugarcane", "Cotton",
               "Jute", "Tea", "Coffee", "Coconut", "Rubber", "Tobacco", "Millets", "Pulses"]
rmse_values = [0.45, 0.38, 0.42, 0.50, 0.55, 0.60, 0.30, 0.65, 0.48, 0.52, 0.58, 0.33, 0.62, 0.70, 0.49, 0.66]
accuracy_values = [92.3, 94.1, 93.0, 90.8, 89.5, 88.0, 96.5, 87.2, 91.5, 90.2, 89.0, 95.0, 86.8, 85.5, 91.0, 86.0]

# Set width and positions
x = np.arange(len(commodities))
width = 0.4

# Plot bars
fig, ax = plt.subplots(figsize=(12, 6))
bars1 = ax.bar(x - width/2, rmse_values, width, label='RMSE', color='red', alpha=0.7)
bars2 = ax.bar(x + width/2, accuracy_values, width, label='Accuracy (%)', color='blue', alpha=0.7)

# Labels and title
ax.set_xlabel('Commodities')
ax.set_ylabel('Values')
ax.set_title('Comparison of RMSE and Accuracy for Each Commodity')
ax.set_xticks(x)
ax.set_xticklabels(commodities, rotation=45, ha='right')
ax.legend()

# Show values on bars
for bar in bars1 + bars2:
    height = bar.get_height()
    ax.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)

# Show plot
plt.tight_layout()
plt.show()
