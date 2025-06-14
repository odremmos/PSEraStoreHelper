# Changelog
PSEraStoreHelper

## [0.1.44] - 2025-06.14
### Changed
- Output of /amazon  to only show a picture.

## [0.1.43] - 2024-05.11
### Changed
- Output of /amazon  to only show a picture.

## [0.1.42] - 2024-05.01
### Changed
- adjusted conditionals for game search

## [0.1.41] - 2024-04.30
### Changed
- loop added to gather_game_data
- changed action config.

## [0.1.4] - 2024-04.26
### Changed
- Maxsize to default for most caches
- Small adjustment to memory garbage collecting
- Reduced lenght of image cache


## [0.1.3] - 2024-04.23
### Added
- Implemented database improvements
### Changed
- Behaviour of determinating the SKU name in /searchpreorder
- Gather Alien Data data pipeline
- Price Determination
- Changed the order of custom_games and out_of_sync games

## [0.1.2] - 2024-04.16
### Added
- Included discounted prices in data gathered
### Changed
- gameinfo displays a different colour and oriiginal price is struck through when discounted
- Better Memory Management
- Data that is gathered through gather_game_data now is using the regional name even if invariant_name is available
- Reduced Game cover image sizes to reduce RAM usage
- Side colour of embeds


## [0.1.1] - 2024-04.16
### Added
- Function to process entries that have missing data
### Changed
- Changed max sizes of caches
- Rating inserts were moved to their own function

## [0.1.0] - 2024-04.14
### Added
- /howlongtobeat
### Changed
- Reworked /help. Now a list of commands and for more specific help it will call an embed with autocomplete
### Fixed
- An error that occurs when looking up certain games that have a different style of store page
- /searchpreorder not searching correctly when there is a single preorder SKU
