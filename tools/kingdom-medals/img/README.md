`medals.webp` is Goodgame Studios' own `SeasonLeagueMedals` sprite strip, pulled
verbatim from the game client:

    https://empire-html5.goodgamestudios.com/default/assets/itemassets/Dialogs/Events/SeasonLeague/SeasonLeagueMedals/SeasonLeagueMedals--<ts>.webp

760x62, eight 95px frames in one row. Frame 0 is the empty/no-medal plate; frames
1-7 are gold, silver, bronze, glass, copper, stone and wood, i.e. frame index ==
the division position that earns that medal. The page crops it with
`background-position`, so the strip ships as-is and nothing is re-encoded.
