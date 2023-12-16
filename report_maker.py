import json
from datetime import datetime
from pprint import pprint as pp


def get_epiweek(date_str):
    # Parse the datetime string
    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

    # Calculate the epiweek
    year_start = datetime(date.year, 1, 1)
    year_start_epiweek_day = year_start.weekday()  # 0 = Monday, 6 = Sunday
    year_start_epiweek_day = (
        year_start_epiweek_day + 1
    ) % 7  # 0 = Sunday, 6 = Saturday
    days_since_year_start = (date - year_start).days
    epiweek = (days_since_year_start + year_start_epiweek_day) // 7 + 1

    return epiweek


def load_disease_data(src_data="data/articles.json"):
    # Load data from json file
    with open(src_data) as file:
        articles = json.load(file)

    # Add the epiweek to each article
    for article in articles["articles"]:
        article["epiweek"] = get_epiweek(article["publishedAt"])

    return articles


def dict_to_md_table(data):
    # Get the column headers from the keys of the first sub-dictionary
    headers = list(next(iter(data.values())).keys())
    headers.sort()
    # Create the markdown table header
    md_table = (
        "| Disease | "
        + " | ".join("Week " + str(header) for header in headers)
        + " |\n"
    )
    md_table += "|-" + "-|" * len(headers) + "-|\n"

    # Create the markdown table rows
    for key, sub_dict in data.items():
        row = (
            "| "
            + str(key)
            + " | "
            + " | ".join(str(sub_dict.get(header, "")) for header in headers)
            + " |\n"
        )
        md_table += row

    return md_table


def gen_report():
    articles = load_disease_data()

    # Count occurence of keywords by epiweek
    epiweeks = sorted(list(set(article["epiweek"] for article in articles["articles"])))
    disease_counts = {}
    last_published = None
    for article in articles["articles"]:
        epiweek = article["epiweek"]
        if last_published == None or article["publishedAt"] > last_published:
            last_published = article["publishedAt"]
        for keyword in article["query"]:
            if keyword not in disease_counts:
                disease_counts[keyword] = {epiweek: 0 for epiweek in epiweeks}
            disease_counts[keyword][epiweek] += 1

    # Start the markdown report
    report = "# Query Keywords Summary Report\n\n"

    # Add the count of new articles at the top of the report
    report += f"- **New articles in last harvest:** {articles['count_articles_new']}\n"

    # Add date of last harvest
    report += f"- **Last harvest:** {articles['last_updated']}\n"

    # Add date of last harvest
    report += f"- **Most recent article:** {last_published}\n\n"

    # Create the markdown table summary
    report += dict_to_md_table(disease_counts)

    # Write the report to a markdown file
    with open("report.md", "w") as f:
        f.write(report)


def main():
    gen_report()


if __name__ == "__main__":
    main()
