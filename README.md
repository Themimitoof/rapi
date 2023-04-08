# Rapi

_Rapi_ is a small script that generate RSS, Atom and (more later) JSON feeds using the Wordpress API.

## Motivation

I mainly made this script after being frustrated by town website that preferred to use a broken service to manage their RSS feeds instead of letting Wordpress doing it.

Unfortunately, a lot of institutions I would like to follow (my town, museums, some tech companies, etc.) have ripped off their RSS feeds from their website that use Wordpress.

Social medias are good mediums to inform and be informed about your interest but nothing is better than an RSS reader where you can't miss any information about a company or a blogger you follow and that's why I made _rapi_.

## Usage

In order to use _Rapi_, you need to have Python and [Poetry](https://python-poetry.org) installed on your computer.

To install all dependencies, simply run the command:

```bash
poetry install
```

To configure _rapi_, make a copy of the file `feeds.example.yml` and call it `feeds.yml`. Inside, you will be able to specify all wordpress websites you want to generate feeds and which feeds formats you would like.

Example:

```yaml
destination: feeds

websites:
  - url: https://www.example.com
    export_formats:
      - rss
      - atom
```

To run _rapi_, simply run the command:

```bash
poetry run rapi
```

If everything goes well, you will find your feeds in the `feeds` folder. You must now make a cron script that execute this script every hour and upload the feeds somewhere accessible by your RSS aggregator or RSS reader app.

## Contributions

This project is open to external contributions. Feel free to submit us a Pull request if you want to contribute and improve with us this project.

In order to maintain an overall good code quality, this project uses the following tools:

- [Black](https://black.readthedocs.io/en/stable/)
- [Ruff](https://beta.ruff.rs/docs/)

Please ensure to run these tools before commiting and submiting a Pull request.

## License

This project is released by under the [BSD-3 license](LICENSE).
