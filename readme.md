# PlayStation Store Helper

A Discord Bot that helps you get information from the PlayStation Store

## Description

This Bot scrapes the PS Store(and more) for various pieces of data and returns the collected data in discord embeds.

It features autocomplete, search and data collection in every regional store as well as collective scraping of multiple regions at once.

This is my first project at this scale, my first in python, my first discord bot. Thus you can expect a lot of ineffecient, redundant and inexperienced code. Although Im quite happy with how it turned out.

The publication of the code is intendend for people interested in coding with python, discord and web scraping.

## Commands

### gameinfo

Returns you a Discord Embed with basic information about a Game

![alt text](https://media.giphy.com/media/1wJ5NXANKALPqRFD1P/giphy.gif "Gif of the command")


### topten

Returns you a Discord Embed with the top ten best selling games of a given region

![alt text](https://media.giphy.com/media/DVqEq2AHA3YNlpYZQp/giphy.gif "Gif of the command")

### searchtpreorders

You can search the bestselling preorder list for a specific game.

Returns you a Discord Embed with the positions if available!

![alt text](https://media.giphy.com/media/MHrfathjwzYEunJ4pn/giphy.gif "Gif of the command")

### screens

Returns you a Discord Embed with the screenshots of a given game

![alt text](https://media.giphy.com/media/HjVCmBWF4cP4d1gk9r/giphy.gif "Gif of the command")



## Also

![](https://i.imgur.com/OBYCZQZ.png)


## Getting Started

### Dependencies

Critically needed to run this bot locally or on a host:

python

Everything in the requirement.txt

A token for the Imgur API

A token for the Discord API

### Config

The code as is requires a token.json with the above mentioned token

#### token:

```
{
    "discord_token": "ImAnDiscordToken",
    "imgur_token": "ImAnImgurToken"
}
```




## Authors

Lacrimosis

[Email](mailto:lacrimosis@proton.me)




## Acknowledgments

Thanks to the various Resetera folks for inspiration and advice.

## Known Issues

Some commands arent working such es the various non PS Store Website scraper.



[<img alt="Deployed with web deploy" src="https://img.shields.io/badge/Deployed With-web deploy-%3CCOLOR%3E?style=for-the-badge&color=2b9348">](https://github.com/SamKirkland/web-deploy)
