# EpiScan

This is a news aggregator project that uses Python and  [News API](https://newsapi.org/) to fetch and process articles on relating to various disease keywords.

## Setup

To set up this project, you'll need to install the required dependencies by running the following command:

```
pip install -r requirements.txt
```

You'll also need to obtain an API key from the [News API](https://newsapi.org/) and set it as an environment variable named `NEWSAPI_KEY`.

## Usage

To run the news aggregator, simply run the `scanner.py` script:

```
python scanner.py
```


This will fetch articles from the News API, process them, and save them to an SQLite database named `epinews.db`. The articles will also be saved to a JSON file named `data/articles.json`.

## Github Actions Workflow

This project includes a Github Actions workflow that runs the `scanner.py` script on a schedule at midnight and midday every day. The workflow is defined in the `.github/workflows/main.yml` file.

The workflow checks out the repository, sets up Python, installs the dependencies, runs the `scanner.py` script, commits the `data/articles.json` and `epinews.db` files, and pushes the changes to the repository.

# Todo

- Add HTML overview of `articles.json`
- Pull keywords out of `scanner.py` and put them into their own config

