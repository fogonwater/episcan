import json
from collections import Counter

# Load the JSON data
with open('data/articles.json') as f:
    data = json.load(f)

# Extract the query keywords
keywords = [keyword for article in data['articles'] for keyword in article['query']]

# Count the occurrences of each keyword
counts = Counter(keywords)

# Start the markdown report
report = "# Query Keywords Summary Report\n\n"

# Sort the counts by value in descending order and add them to the report
for keyword, count in counts.most_common():
    report += f"* **{keyword}:** {count} articles\n"

# Write the report to a markdown file
with open('report.md', 'w') as f:
    f.write(report)