#!/usr/bin/env python3
"""
NJ Baseball Savant - Stats Scraper
Pulls hitting/pitching data from highschoolsports.nj.com and computes advanced metrics.

Usage:
  python3 scraper.py                        # scrape all teams in TEAMS dict
  python3 scraper.py west-orange-west-orange  # scrape one team by slug
"""

import urllib.request
import ssl
import certifi
import re
import json
import sys
import time
from html import unescape

# ── LEAGUE CONSTANTS ───────────────────────────────────────────────────────────
SEASON       = "2025-2026"
WOBA_SCALE   = 1.12
WOBA_LEAGUE  = 0.353   # league-average wOBA (adjust each season)
R_PA_LEAGUE  = 0.177   # league runs/PA  (adjust each season)

# ── TEAMS TO SCRAPE ────────────────────────────────────────────────────────────
# Generated from NJ.com standings conference pages for the current season.
# Format: "Display Name" -> "url-slug"
TEAMS = {
    # ── BCSL ───────────────────────────────────
    "Bordentown": "bordentown-bordentown",
    "Burlington City": "burlington-burlington-city",
    "Burlington Township": "burlington-twp-burlington-township",
    "Cinnaminson": "cinnaminson-cinnaminson",
    "Delran": "delran-delran",
    "Doane Academy": "burlington-doane-academy",
    "Florence": "florence-florence",
    "Holy Cross Prep": "delran-holy-cross-prep",
    "Maple Shade": "maple-shade-maple-shade",
    "Medford Tech": "medford-medford-tech",
    "Moorestown Friends": "moorestown-moorestown-friends",
    "Northern Burlington": "columbus-northern-burlington",
    "Palmyra": "palmyra-palmyra",
    "Pemberton": "pemberton-pemberton",
    "Pennsauken": "pennsauken-pennsauken",
    "Pennsauken Tech": "pennsauken-pennsauken-tech",
    "Riverside": "riverside-riverside",
    "Westampton Tech": "westampton-westampton-tech",
    "Willingboro": "willingboro-willingboro",
    # ── Big North ───────────────────────────────────
    "Bergen Catholic": "oradell-bergen-catholic",
    "Bergen Tech": "hackensack-bergen-tech",
    "Bergenfield": "bergenfield-bergenfield",
    "Cliffside Park": "cliffside-park-cliffside-park",
    "Clifton": "clifton-clifton",
    "DePaul": "wayne-depaul",
    "Demarest": "demarest-demarest",
    "Don Bosco Prep": "ramsey-don-bosco-prep",
    "Dumont": "dumont-dumont",
    "Dwight-Morrow": "englewood-dwight-morrow",
    "Fair Lawn": "fair-lawn-fair-lawn",
    "Fort Lee": "fort-lee-fort-lee",
    "Hackensack": "hackensack-hackensack",
    "Indian Hills": "oakland-indian-hills",
    "Lakeland": "wanaque-lakeland",
    "Mahwah": "mahwah-mahwah",
    "Northern Highlands": "allendale-northern-highlands",
    "Old Tappan": "old-tappan-old-tappan",
    "Paramus": "paramus-paramus",
    "Paramus Catholic": "paramus-paramus-catholic",
    "Pascack Hills": "montvale-pascack-hills",
    "Pascack Valley": "hillsdale-pascack-valley",
    "Passaic": "passaic-passaic",
    "Passaic Tech": "wayne-passaic-tech",
    "Passaic Valley": "little-falls-passaic-valley",
    "Paterson Eastside": "paterson-paterson-eastside",
    "Paterson Kennedy": "paterson-paterson-kennedy",
    "Ramapo": "franklin-lakes-ramapo",
    "Ramsey": "ramsey-ramsey",
    "Ridgefield Park/Bogota": "ridgefield-park-ridgefield-park",
    "Ridgewood": "ridgewood-ridgewood",
    "River Dell": "oradell-river-dell",
    "St. Joseph (Mont.)": "montvale-st-joseph-mont",
    "Teaneck": "teaneck-teaneck",
    "Tenafly": "tenafly-tenafly",
    "Wayne Hills": "wayne-wayne-hills",
    "Wayne Valley": "wayne-wayne-valley",
    "West Milford": "west-milford-west-milford",
    "Westwood": "washington-twp-westwood",
    # ── CVC ───────────────────────────────────
    "Allentown": "allentown-allentown",
    "Ewing": "ewing-ewing",
    "Hamilton West": "hamilton-hamilton-west",
    "Hightstown": "hightstown-hightstown",
    "Hopewell Valley": "pennington-hopewell-valley",
    "Lawrence": "lawrenceville-lawrence",
    "Notre Dame": "lawrenceville-notre-dame",
    "Nottingham": "hamilton-nottingham",
    "Princeton": "princeton-princeton",
    "Princeton Day": "princeton-princeton-day",
    "Robbinsville": "robbinsville-robbinsville",
    "Steinert": "hamilton-steinert",
    "Trenton": "trenton-trenton",
    "West Windsor-Plainsboro North": "plainsboro-west-windsor-plainsboro-north",
    "West Windsor-Plainsboro South": "princeton-jct-west-windsor-plainsboro-south",
    # ── Cape-Atlantic ───────────────────────────────────
    "Absegami": "galloway-absegami",
    "Atlantic City": "atlantic-city-atlantic-city",
    "Atlantic Tech": "mays-landing-atlantic-tech",
    "Bridgeton": "bridgeton-bridgeton",
    "Buena": "buena-buena",
    "Cape May Tech": "cape-may-ct-hse-cape-may-tech",
    "Cedar Creek": "egg-harbor-city-cedar-creek",
    "Egg Harbor": "egg-harbor-twp-egg-harbor",
    "Hammonton": "hammonton-hammonton",
    "Holy Spirit": "absecon-holy-spirit",
    "Lower Cape May": "erma-lower-cape-may",
    "Mainland": "linwood-mainland",
    "Middle Township": "cape-may-ct-hse-middle-township",
    "Millville": "millville-millville",
    "Oakcrest": "mays-landing-oakcrest",
    "Ocean City": "ocean-city-ocean-city",
    "Pleasantville": "pleasantville-pleasantville",
    "St. Augustine": "richland-st-augustine",
    "St. Joseph (Hamm.)": "hammonton-st-joseph-hamm",
    "Vineland": "vineland-vineland",
    "Wildwood Catholic": "n-wildwood-wildwood-catholic",
    # ── Colonial ───────────────────────────────────
    "Audubon": "audubon-audubon",
    "Collingswood": "collingswood-collingswood",
    "Gateway": "woodbury-hts-gateway",
    "Gloucester": "gloucester-city-gloucester",
    "Haddon Heights": "haddon-heights-haddon-heights",
    "Haddon Township": "westmont-haddon-township",
    "Haddonfield": "haddonfield-haddonfield",
    "Paulsboro": "paulsboro-paulsboro",
    "Sterling": "somerdale-sterling",
    "West Deptford": "westville-west-deptford",
    # ── GMC ───────────────────────────────────
    "Carteret": "carteret-carteret",
    "Colonia": "colonia-colonia",
    "Dunellen": "dunellen-dunellen",
    "East Brunswick": "east-brunswick-east-brunswick",
    "East Brunswick Magnet": "east-brunswick-east-brunswick-tech",
    "Edison": "edison-edison",
    "Highland Park": "highland-park-highland-park",
    "Iselin Kennedy": "iselin-iselin-kennedy",
    "J.P. Stevens": "edison-jp-stevens",
    "Metuchen": "metuchen-metuchen",
    "Middlesex": "middlesex-middlesex",
    "Monroe": "monroe-twp-monroe",
    "New Brunswick": "new-brunswick-new-brunswick",
    "North Brunswick": "north-brunswick-north-brunswick",
    "North Plainfield": "no-plainfield-north-plainfield",
    "Old Bridge": "matawan-old-bridge",
    "Perth Amboy": "perth-amboy-perth-amboy",
    "Perth Amboy Magnet": "perth-amboy-perth-amboy-tech",
    "Piscataway": "piscataway-piscataway",
    "Piscataway Magnet": "piscataway-piscataway-tech",
    "Sayreville": "parlin-sayreville",
    "Somerset Tech": "bridgewater-somerset-tech",
    "South Amboy": "south-amboy-south-amboy",
    "South Brunswick": "monmouth-jct-south-brunswick",
    "South Plainfield": "so-plainfield-south-plainfield",
    "South River": "south-river-south-river",
    "Spotswood": "spotswood-spotswood",
    "St. Joseph (Met.)": "metuchen-st-joseph-met",
    "St. Thomas Aquinas": "edison-st-thomas-aquinas-formerly-bishop-ahr",
    "Timothy Christian/Roselle Catholic": "piscataway-timothy-christian",
    "Wardlaw-Hartridge": "edison-wardlaw-hartridge",
    "Woodbridge": "woodbridge-woodbridge",
    # ── HCIAL ───────────────────────────────────
    "Bayonne": "bayonne-bayonne",
    "Dickinson": "jersey-city-dickinson",
    "Ferris": "jersey-city-ferris",
    "Hoboken": "hoboken-hoboken",
    "Hudson Catholic": "jersey-city-hudson-catholic",
    "Kearny": "kearny-kearny",
    "Lincoln": "jersey-city-lincoln",
    "McNair": "jersey-city-mcnair",
    "Memorial": "west-new-york-memorial",
    "North Bergen": "north-bergen-north-bergen",
    "Snyder": "jersey-city-snyder",
    "St. Peter's Prep": "jersey-city-st-peters-prep",
    "Union City": "union-city-union-city",
    "University Charter": "jersey-city-university-charter",
    # ── NJAC ───────────────────────────────────
    "Boonton": "boonton-boonton",
    "Chatham": "chatham-chatham",
    "Delbarton": "morristown-delbarton",
    "Dover": "dover-dover",
    "Hackettstown": "hackettstown-hackettstown",
    "Hanover Park": "east-hanover-hanover-park",
    "High Point": "sussex-high-point",
    "Hopatcong": "hopatcong-hopatcong",
    "Jefferson": "oak-ridge-jefferson",
    "Kinnelon": "kinnelon-kinnelon",
    "Kittatinny": "newton-kittatinny",
    "Lenape Valley": "stanhope-lenape-valley",
    "Madison": "madison-madison",
    "Mendham": "mendham-mendham",
    "Montville": "montville-montville",
    "Morris Catholic": "denville-morris-catholic",
    "Morris Hills": "rockaway-morris-hills",
    "Morris Knolls": "rockaway-morris-knolls",
    "Morris Tech": "denville-morris-tech",
    "Morristown": "morristown-morristown",
    "Morristown-Beard": "morristown-morristown-beard",
    "Mount Olive": "flanders-mount-olive",
    "Mountain Lakes": "mountain-lakes-mountain-lakes",
    "Newton": "newton-newton",
    "North Warren": "blairstown-north-warren",
    "Parsippany": "parsippany-parsippany",
    "Parsippany Hills": "morris-plains-parsippany-hills",
    "Pequannock": "pompton-plains-pequannock",
    "Pope John": "sparta-pope-john",
    "Randolph": "randolph-randolph",
    "Roxbury": "succasunna-roxbury",
    "Sparta": "sparta-sparta",
    "Sussex Tech": "sparta-sussex-tech",
    "Vernon": "vernon-vernon",
    "Wallkill Valley": "hamburg-wallkill-valley",
    "West Morris": "chester-west-morris",
    "Whippany Park": "whippany-whippany-park",
    # ── NJIC ───────────────────────────────────
    "Becton": "east-rutherford-becton",
    "Butler": "butler-butler",
    "Cresskill": "cresskill-cresskill",
    "Dwight-Englewood": "englewood-dwight-englewood",
    "Elmwood Park": "elmwood-park-elmwood-park",
    "Emerson Boro": "emerson-emerson-boro",
    "Garfield": "garfield-garfield",
    "Glen Rock": "glen-rock-glen-rock",
    "Harrison": "harrison-harrison",
    "Hasbrouck Heights": "hasbrouck-hts-hasbrouck-heights",
    "Hawthorne": "hawthorne-hawthorne",
    "Hawthorne Christian/Eastern Christian": "hawthorne-hawthorne-christian",
    "Leonia": "leonia-leonia",
    "Lodi": "lodi-lodi",
    "Lyndhurst": "lyndhurst-lyndhurst",
    "Manchester Regional": "haledon-manchester-regional",
    "Midland Park": "midland-park-midland-park",
    "New Milford": "new-milford-new-milford",
    "North Arlington": "north-arlington-north-arlington",
    "Park Ridge": "park-ridge-park-ridge",
    "Paterson Charter": "paterson-paterson-charter",
    "Pompton Lakes": "pompton-lakes-pompton-lakes",
    "Ridgefield/Palisades Park": "ridgefield-ridgefield",
    "Rutherford": "rutherford-rutherford",
    "Saddle Brook": "saddle-brook-saddle-brook",
    "Secaucus": "secaucus-secaucus",
    "St. Mary (Ruth.)": "rutherford-st-mary-ruth",
    "Waldwick": "waldwick-waldwick",
    "Wallington": "wallington-wallington",
    "Weehawken": "weehawken-weehawken",
    "Wood-Ridge": "wood-ridge-wood-ridge",
    # ── Olympic ───────────────────────────────────
    "Bishop Eustace": "pennsauken-bishop-eustace",
    "Camden Catholic": "cherry-hill-camden-catholic",
    "Cherokee": "marlton-cherokee",
    "Cherry Hill East": "cherry-hill-cherry-hill-east",
    "Cherry Hill West": "cherry-hill-cherry-hill-west",
    "Eastern": "voorhees-eastern",
    "Lenape": "medford-lenape",
    "Moorestown": "moorestown-moorestown",
    "Paul VI": "haddonfield-paul-vi",
    "Rancocas Valley": "mount-holly-rancocas-valley",
    "Seneca": "tabernacle-seneca",
    "Shawnee": "medford-shawnee",
    # ── SEC ───────────────────────────────────
    "Barringer": "newark-barringer",
    "Belleville": "belleville-belleville",
    "Bloomfield": "bloomfield-bloomfield",
    "Caldwell": "west-caldwell-caldwell",
    "Cedar Grove": "cedar-grove-cedar-grove",
    "Columbia": "maplewood-columbia",
    "East Orange": "east-orange-east-orange",
    "Glen Ridge": "glen-ridge-glen-ridge",
    "Golda Och": "west-orange-golda-och",
    "Livingston": "livingston-livingston",
    "Millburn": "millburn-millburn",
    "Montclair": "montclair-montclair",
    "Montclair Kimberley": "montclair-montclair-kimberley",
    "Newark Academy": "livingston-newark-academy",
    "Newark Central": "newark-newark-central",
    "Newark East Side": "newark-newark-east-side",
    "Newark Tech": "newark-newark-tech",
    "North Star Academy": "newark-north-star-academy",
    "Nutley": "nutley-nutley",
    "Orange": "orange-orange",
    "Payne Tech": "newark-payne-tech",
    "Seton Hall Prep": "west-orange-seton-hall-prep",
    "Shabazz": "newark-shabazz",
    "St. Benedict's": "newark-st-benedicts",
    "Technology": "newark-technology",
    "University": "newark-university",
    "Verona": "verona-verona",
    "Weequahic": "newark-weequahic",
    "West Essex": "north-caldwell-west-essex",
    "West Orange": "west-orange-west-orange",
    # ── Shore ───────────────────────────────────
    "Asbury Park": "asbury-park-asbury-park",
    "Barnegat": "barnegat-barnegat",
    "Brick Memorial": "brick-brick-memorial",
    "Brick Township": "brick-brick-township",
    "Central Regional": "bayville-central-regional",
    "Christian Brothers": "lincroft-christian-brothers",
    "Colts Neck": "colts-neck-colts-neck",
    "Donovan Catholic": "toms-river-donovan-catholic",
    "Freehold Borough": "freehold-freehold-borough",
    "Freehold Township": "freehold-freehold-township",
    "Henry Hudson": "highlands-henry-hudson",
    "Holmdel": "holmdel-holmdel",
    "Howell": "farmingdale-howell",
    "Jackson Township": "jackson-jackson-township",
    "Keansburg": "keansburg-keansburg",
    "Keyport": "keyport-keyport",
    "Lacey": "lanoka-harbor-lacey",
    "Lakewood": "lakewood-lakewood",
    "Long Branch": "long-branch-long-branch",
    "Manalapan": "manalapan-manalapan",
    "Manasquan": "manasquan-manasquan",
    "Manchester Township": "manchester-manchester-township",
    "Marlboro": "marlboro-marlboro",
    "Matawan": "aberdeen-matawan",
    "Middletown North": "middletown-middletown-north",
    "Middletown South": "middletown-middletown-south",
    "Monmouth": "tinton-falls-monmouth",
    "Neptune": "neptune-neptune",
    "New Egypt": "new-egypt-new-egypt",
    "Ocean Township": "oakhurst-ocean-township",
    "Pinelands": "tuckerton-pinelands",
    "Point Pleasant Beach": "pt-pleasant-bch-point-pleasant-beach",
    "Point Pleasant Boro": "pt-pleasant-point-pleasant-boro",
    "Ranney": "tinton-falls-ranney",
    "Raritan": "hazlet-raritan",
    "Red Bank Catholic": "red-bank-red-bank-catholic",
    "Red Bank Regional": "little-silver-red-bank-regional",
    "Rumson-Fair Haven": "rumson-rumson-fair-haven",
    "Shore": "w-long-branch-shore",
    "Southern": "manahawkin-southern",
    "St. John Vianney": "holmdel-st-john-vianney",
    "St. Rose": "belmar-st-rose",
    "Toms River East": "toms-river-toms-river-east",
    "Toms River North": "toms-river-toms-river-north",
    "Toms River South": "toms-river-toms-river-south",
    "Wall": "wall-wall",
    # ── Skyland ───────────────────────────────────
    "Belvidere": "belvidere-belvidere",
    "Bernards": "bernardsville-bernards",
    "Bound Brook": "bound-brook-bound-brook",
    "Bridgewater-Raritan": "bridgewater-bridgewater-raritan",
    "Delaware Valley": "alexandria-delaware-valley",
    "Franklin": "somerset-franklin",
    "Gill St. Bernard's": "gladstone-gill-st-bernards",
    "Hillsborough": "hillsborough-hillsborough",
    "Hunterdon Central": "flemington-hunterdon-central",
    "Immaculata": "somerville-immaculata",
    "Manville": "manville-manville",
    "Montgomery": "skillman-montgomery",
    "North Hunterdon": "annandale-north-hunterdon",
    "Phillipsburg": "phillipsburg-phillipsburg",
    "Pingry": "martinsville-pingry",
    "Ridge": "basking-ridge-ridge",
    "Rutgers Prep": "somerset-rutgers-prep",
    "Somerville": "somerville-somerville",
    "South Hunterdon": "lambertville-south-hunterdon",
    "Voorhees": "glen-gardner-voorhees",
    "Warren Hills": "washington-warren-hills",
    "Watchung Hills": "warren-watchung-hills",
    # ── Tri-County ───────────────────────────────────
    "Clayton": "clayton-clayton",
    "Clearview": "mullica-hill-clearview",
    "Cumberland": "seabrook-cumberland",
    "Delsea": "franklinville-delsea",
    "Deptford": "deptford-deptford",
    "Glassboro": "glassboro-glassboro",
    "Gloucester Catholic": "gloucester-city-gloucester-catholic",
    "Gloucester Tech": "sewell-gloucester-tech",
    "Highland": "blackwood-highland",
    "Kingsway": "woolwich-twp-kingsway",
    "Overbrook": "pine-hill-overbrook",
    "Penns Grove": "carneys-point-penns-grove",
    "Pennsville": "pennsville-pennsville",
    "Pitman": "pitman-pitman",
    "Salem": "salem-salem",
    "Schalick": "pittsgrove-schalick",
    "Timber Creek": "erial-timber-creek",
    "Triton": "runnemede-triton",
    "Washington Township": "sewell-washington-township",
    "Wildwood": "wildwood-wildwood",
    "Williamstown": "williamstown-williamstown",
    "Woodstown": "woodstown-woodstown",
    # ── UCC ───────────────────────────────────
    "Brearley": "kenilworth-brearley",
    "Cranford": "cranford-cranford",
    "Dayton": "springfield-dayton",
    "Elizabeth": "elizabeth-elizabeth",
    "Gov. Livingston": "berkeley-hts-gov-livingston",
    "Hillside": "hillside-hillside",
    "Johnson": "clark-johnson",
    "Linden": "linden-linden",
    "New Providence": "new-providence-new-providence",
    "Oratory": "summit-oratory",
    "Plainfield": "plainfield-plainfield",
    "Rahway": "rahway-rahway",
    "Roselle Park": "roselle-park-roselle-park",
    "Scotch Plains-Fanwood": "scotch-plains-scotch-plains-fanwood",
    "Summit": "summit-summit",
    "Union": "union-union",
    "Union Catholic": "scotch-plains-union-catholic",
    "Westfield": "westfield-westfield",
}

TEAM_META = {
    "Bordentown": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2692.png"},
    "Burlington City": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2739.png"},
    "Burlington Township": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2742.png"},
    "Cinnaminson": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2847.png"},
    "Delran": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2948.png"},
    "Doane Academy": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6330.png"},
    "Florence": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3133.png"},
    "Holy Cross Prep": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5161.png"},
    "Maple Shade": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3778.png"},
    "Medford Tech": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6311.png"},
    "Moorestown Friends": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6315.png"},
    "Northern Burlington": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4048.png"},
    "Palmyra": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4237.png"},
    "Pemberton": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4274.png"},
    "Pennsauken": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4278.png"},
    "Pennsauken Tech": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6323.png"},
    "Riverside": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4409.png"},
    "Westampton Tech": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6337.png"},
    "Willingboro": {"div": "BCSL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4912.png"},
    "Bergen Catholic": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5083.png"},
    "Bergen Tech": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2658.png"},
    "Bergenfield": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2662.png"},
    "Cliffside Park": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2868.png"},
    "Clifton": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2872.png"},
    "DePaul": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6044.png"},
    "Demarest": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4050.png"},
    "Don Bosco Prep": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5102.png"},
    "Dumont": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2987.png"},
    "Dwight-Morrow": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2996.png"},
    "Fair Lawn": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3111.png"},
    "Fort Lee": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3146.png"},
    "Hackensack": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3287.png"},
    "Indian Hills": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3448.png"},
    "Lakeland": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3615.png"},
    "Mahwah": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3755.png"},
    "Northern Highlands": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4049.png"},
    "Old Tappan": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4028.png"},
    "Paramus": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4239.png"},
    "Paramus Catholic": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5092.png"},
    "Pascack Hills": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4257.png"},
    "Pascack Valley": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4258.png"},
    "Passaic": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4261.png"},
    "Passaic Tech": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4260.png"},
    "Passaic Valley": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4264.png"},
    "Paterson Eastside": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3026.png"},
    "Paterson Kennedy": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3528.png"},
    "Ramapo": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4353.png"},
    "Ramsey": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4355.png"},
    "Ridgefield Park/Bogota": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4396.png"},
    "Ridgewood": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4399.png"},
    "River Dell": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4404.png"},
    "St. Joseph (Mont.)": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5067.png"},
    "Teaneck": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4631.png"},
    "Tenafly": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4633.png"},
    "Wayne Hills": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4835.png"},
    "Wayne Valley": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4836.png"},
    "West Milford": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4859.png"},
    "Westwood": {"div": "Big North", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4874.png"},
    "Allentown": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2554.png"},
    "Ewing": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3106.png"},
    "Hamilton West": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3302.png"},
    "Hightstown": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3378.png"},
    "Hopewell Valley": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6244.png"},
    "Lawrence": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3637.png"},
    "Notre Dame": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5555.png"},
    "Nottingham": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3301.png"},
    "Princeton": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4331.png"},
    "Princeton Day": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6247.png"},
    "Robbinsville": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4414.png"},
    "Steinert": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3300.png"},
    "Trenton": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4694.png"},
    "West Windsor-Plainsboro North": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4866.png"},
    "West Windsor-Plainsboro South": {"div": "CVC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4867.png"},
    "Absegami": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2498.png"},
    "Atlantic City": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2593.png"},
    "Atlantic Tech": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/7537.png"},
    "Bridgeton": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2713.png"},
    "Buena": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2737.png"},
    "Cape May Tech": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2767.png"},
    "Cedar Creek": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6947.png"},
    "Egg Harbor": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3042.png"},
    "Hammonton": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3305.png"},
    "Holy Spirit": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4973.png"},
    "Lower Cape May": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3731.png"},
    "Mainland": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3758.png"},
    "Middle Township": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3894.png"},
    "Millville": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3922.png"},
    "Oakcrest": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4193.png"},
    "Ocean City": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4202.png"},
    "Pleasantville": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4314.png"},
    "St. Augustine": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4976.png"},
    "St. Joseph (Hamm.)": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4992.png"},
    "Vineland": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4752.png"},
    "Wildwood Catholic": {"div": "Cape-Atlantic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5284.png"},
    "Audubon": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2601.png"},
    "Collingswood": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2882.png"},
    "Gateway": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3209.png"},
    "Gloucester": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3243.png"},
    "Haddon Heights": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3290.png"},
    "Haddon Township": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3291.png"},
    "Haddonfield": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3292.png"},
    "Paulsboro": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4270.png"},
    "Sterling": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4594.png"},
    "West Deptford": {"div": "Colonial", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4849.png"},
    "Carteret": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2776.png"},
    "Colonia": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2884.png"},
    "Dunellen": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2988.png"},
    "East Brunswick": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3009.png"},
    "East Brunswick Magnet": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3010.png"},
    "Edison": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3031.png"},
    "Highland Park": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3375.png"},
    "Iselin Kennedy": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3471.png"},
    "J.P. Stevens": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3479.png"},
    "Metuchen": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3885.png"},
    "Middlesex": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3897.png"},
    "Monroe": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3937.png"},
    "New Brunswick": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4004.png"},
    "North Brunswick": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4037.png"},
    "North Plainfield": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4044.png"},
    "Old Bridge": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4212.png"},
    "Perth Amboy": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4289.png"},
    "Perth Amboy Magnet": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4290.png"},
    "Piscataway": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4306.png"},
    "Piscataway Magnet": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4307.png"},
    "Sayreville": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6254.png"},
    "Somerset Tech": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4538.png"},
    "South Amboy": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4546.png"},
    "South Brunswick": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4547.png"},
    "South Plainfield": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4556.png"},
    "South River": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4559.png"},
    "Spotswood": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4581.png"},
    "St. Joseph (Met.)": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5623.png"},
    "St. Thomas Aquinas": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5596.png"},
    "Timothy Christian/Roselle Catholic": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6331.png"},
    "Wardlaw-Hartridge": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6336.png"},
    "Woodbridge": {"div": "GMC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4933.png"},
    "Bayonne": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2629.png"},
    "Dickinson": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4906.png"},
    "Ferris": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3488.png"},
    "Hoboken": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3400.png"},
    "Hudson Catholic": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5468.png"},
    "Kearny": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3573.png"},
    "Lincoln": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3683.png"},
    "McNair": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2982.png"},
    "Memorial": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3864.png"},
    "North Bergen": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4035.png"},
    "Snyder": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3361.png"},
    "St. Peter's Prep": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5489.png"},
    "Union City": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6402.png"},
    "University Charter": {"div": "HCIAL", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6333.png"},
    "Boonton": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2690.png"},
    "Chatham": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2826.png"},
    "Delbarton": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6255.png"},
    "Dover": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2972.png"},
    "Hackettstown": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3288.png"},
    "Hanover Park": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3309.png"},
    "High Point": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3371.png"},
    "Hopatcong": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3413.png"},
    "Jefferson": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3510.png"},
    "Kinnelon": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3586.png"},
    "Kittatinny": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3589.png"},
    "Lenape Valley": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3646.png"},
    "Madison": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3749.png"},
    "Mendham": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4861.png"},
    "Montville": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3943.png"},
    "Morris Catholic": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5829.png"},
    "Morris Hills": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3954.png"},
    "Morris Knolls": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3955.png"},
    "Morris Tech": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6316.png"},
    "Morristown": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3956.png"},
    "Morristown-Beard": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6256.png"},
    "Mount Olive": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3961.png"},
    "Mountain Lakes": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3966.png"},
    "Newton": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4021.png"},
    "North Warren": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4045.png"},
    "Parsippany": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4254.png"},
    "Parsippany Hills": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4255.png"},
    "Pequannock": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4284.png"},
    "Pope John": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6157.png"},
    "Randolph": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4360.png"},
    "Roxbury": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4462.png"},
    "Sparta": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4577.png"},
    "Sussex Tech": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4617.png"},
    "Vernon": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4741.png"},
    "Wallkill Valley": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4768.png"},
    "West Morris": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4860.png"},
    "Whippany Park": {"div": "NJAC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4876.png"},
    "Becton": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3360.png"},
    "Butler": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2747.png"},
    "Cresskill": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2920.png"},
    "Dwight-Englewood": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6300.png"},
    "Elmwood Park": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3873.png"},
    "Emerson Boro": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3067.png"},
    "Garfield": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3208.png"},
    "Glen Rock": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3235.png"},
    "Harrison": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3322.png"},
    "Hasbrouck Heights": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3328.png"},
    "Hawthorne": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3339.png"},
    "Hawthorne Christian/Eastern Christian": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6302.png"},
    "Leonia": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3650.png"},
    "Lodi": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3713.png"},
    "Lyndhurst": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3740.png"},
    "Manchester Regional": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3765.png"},
    "Midland Park": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3903.png"},
    "New Milford": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4011.png"},
    "North Arlington": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4033.png"},
    "Park Ridge": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4244.png"},
    "Paterson Charter": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/8392.png"},
    "Pompton Lakes": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4321.png"},
    "Ridgefield/Palisades Park": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4395.png"},
    "Rutherford": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4466.png"},
    "Saddle Brook": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4469.png"},
    "Secaucus": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4505.png"},
    "St. Mary (Ruth.)": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5120.png"},
    "Waldwick": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4762.png"},
    "Wallington": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4767.png"},
    "Weehawken": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4839.png"},
    "Wood-Ridge": {"div": "NJIC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4951.png"},
    "Bishop Eustace": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5256.png"},
    "Camden Catholic": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5214.png"},
    "Cherokee": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2831.png"},
    "Cherry Hill East": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2833.png"},
    "Cherry Hill West": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2834.png"},
    "Eastern": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3023.png"},
    "Lenape": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3644.png"},
    "Moorestown": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3946.png"},
    "Paul VI": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5246.png"},
    "Rancocas Valley": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4357.png"},
    "Seneca": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4508.png"},
    "Shawnee": {"div": "Olympic", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4517.png"},
    "Barringer": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2623.png"},
    "Belleville": {"div": "SEC", "mascot": "", "p": "#1a2a6b", "s": "#c8960c", "t": "#f0c040", "bg": "#06091a", "logo": "logos/belleville.png"},
    "Bloomfield": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2683.png"},
    "Caldwell": {"div": "SEC", "mascot": "", "p": "#1a35a0", "s": "#2a50c8", "t": "#80a8e8", "bg": "#060d28", "logo": "logos/caldwell.png"},
    "Cedar Grove": {"div": "SEC", "mascot": "", "p": "#1a1500", "s": "#c8960c", "t": "#f0c040", "bg": "#0e0b00", "logo": "logos/cedar-grove.png"},
    "Columbia": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2890.png"},
    "East Orange": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3018.png"},
    "Glen Ridge": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3234.png"},
    "Golda Och": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6327.png"},
    "Livingston": {"div": "SEC", "mascot": "", "p": "#1a5a1a", "s": "#2a8a2a", "t": "#70c870", "bg": "#071507", "logo": "logos/livingston.png"},
    "Millburn": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3915.png"},
    "Montclair": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3939.png"},
    "Montclair Kimberley": {"div": "SEC", "mascot": "", "p": "#1a2a6b", "s": "#7a6030", "t": "#b09060", "bg": "#07091e", "logo": "logos/mka.png"},
    "Newark Academy": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6253.png"},
    "Newark Central": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2806.png"},
    "Newark East Side": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3019.png"},
    "Newark Tech": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6318.png"},
    "North Star Academy": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6414.png"},
    "Nutley": {"div": "SEC", "mascot": "", "p": "#8b1a2a", "s": "#b02535", "t": "#d07080", "bg": "#1a0508", "logo": "logos/nutley.png"},
    "Orange": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4222.png"},
    "Payne Tech": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/9906.png"},
    "Seton Hall Prep": {"div": "SEC", "mascot": "", "p": "#1a2a8b", "s": "#2a50c8", "t": "#8090e8", "bg": "#06091e", "logo": "logos/shp.png"},
    "Shabazz": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3760.png"},
    "St. Benedict's": {"div": "SEC", "mascot": "", "p": "#6b1520", "s": "#8b1a28", "t": "#c08088", "bg": "#150508", "logo": "logos/sbp.png"},
    "Technology": {"div": "SEC", "mascot": "", "p": "#1a1a1a", "s": "#444444", "t": "#cccccc", "bg": "#0a0a0a", "logo": "logos/technology.png"},
    "University": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4713.png"},
    "Verona": {"div": "SEC", "mascot": "", "p": "#7a1010", "s": "#a01818", "t": "#d47070", "bg": "#1e0505", "logo": "logos/verona.png"},
    "Weequahic": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4840.png"},
    "West Essex": {"div": "SEC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4855.png"},
    "West Orange": {"div": "SEC", "mascot": "", "p": "#1e3a6e", "s": "#4a7cc7", "t": "#a8c8f0", "bg": "#0a1628", "logo": "logos/west-orange.png"},
    "Asbury Park": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2587.png"},
    "Barnegat": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2622.png"},
    "Brick Memorial": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2712.png"},
    "Brick Township": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2711.png"},
    "Central Regional": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2811.png"},
    "Christian Brothers": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5767.png"},
    "Colts Neck": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2887.png"},
    "Donovan Catholic": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5976.png"},
    "Freehold Borough": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3188.png"},
    "Freehold Township": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3191.png"},
    "Henry Hudson": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3359.png"},
    "Holmdel": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3409.png"},
    "Howell": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3426.png"},
    "Jackson Township": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/12815.png"},
    "Keansburg": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3572.png"},
    "Keyport": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3579.png"},
    "Lacey": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3598.png"},
    "Lakewood": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3619.png"},
    "Long Branch": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3716.png"},
    "Manalapan": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3761.png"},
    "Manasquan": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3764.png"},
    "Manchester Township": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3766.png"},
    "Marlboro": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3793.png"},
    "Matawan": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3818.png"},
    "Middletown North": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3898.png"},
    "Middletown South": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3899.png"},
    "Monmouth": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3935.png"},
    "Neptune": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4000.png"},
    "New Egypt": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4006.png"},
    "Ocean Township": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4206.png"},
    "Pinelands": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4303.png"},
    "Point Pleasant Beach": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4317.png"},
    "Point Pleasant Boro": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4318.png"},
    "Ranney": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6324.png"},
    "Raritan": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4364.png"},
    "Red Bank Catholic": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5795.png"},
    "Red Bank Regional": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4375.png"},
    "Rumson-Fair Haven": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4464.png"},
    "Shore": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4522.png"},
    "Southern": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4572.png"},
    "St. John Vianney": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5716.png"},
    "St. Rose": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5700.png"},
    "Toms River East": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4685.png"},
    "Toms River North": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4686.png"},
    "Toms River South": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4687.png"},
    "Wall": {"div": "Shore", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4764.png"},
    "Belvidere": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2651.png"},
    "Bernards": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2669.png"},
    "Bound Brook": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2694.png"},
    "Bridgewater-Raritan": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2714.png"},
    "Delaware Valley": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2947.png"},
    "Franklin": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3177.png"},
    "Gill St. Bernard's": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6301.png"},
    "Hillsborough": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3387.png"},
    "Hunterdon Central": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3435.png"},
    "Immaculata": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6134.png"},
    "Manville": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3774.png"},
    "Montgomery": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3940.png"},
    "North Hunterdon": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4042.png"},
    "Phillipsburg": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4296.png"},
    "Pingry": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6249.png"},
    "Ridge": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4391.png"},
    "Rutgers Prep": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6325.png"},
    "Somerville": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4543.png"},
    "South Hunterdon": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4551.png"},
    "Voorhees": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4757.png"},
    "Warren Hills": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4793.png"},
    "Watchung Hills": {"div": "Skyland", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4832.png"},
    "Clayton": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2858.png"},
    "Clearview": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2861.png"},
    "Cumberland": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2927.png"},
    "Delsea": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2951.png"},
    "Deptford": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2958.png"},
    "Glassboro": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3229.png"},
    "Gloucester Catholic": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/5232.png"},
    "Gloucester Tech": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3245.png"},
    "Highland": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3374.png"},
    "Kingsway": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3583.png"},
    "Overbrook": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4229.png"},
    "Penns Grove": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4276.png"},
    "Pennsville": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4282.png"},
    "Pitman": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4308.png"},
    "Salem": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4472.png"},
    "Schalick": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2581.png"},
    "Timber Creek": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4679.png"},
    "Triton": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4696.png"},
    "Washington Township": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4829.png"},
    "Wildwood": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4892.png"},
    "Williamstown": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4910.png"},
    "Woodstown": {"div": "Tri-County", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4965.png"},
    "Brearley": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2933.png"},
    "Cranford": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2916.png"},
    "Dayton": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3547.png"},
    "Elizabeth": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3055.png"},
    "Gov. Livingston": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3251.png"},
    "Hillside": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3396.png"},
    "Johnson": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/2579.png"},
    "Linden": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/3697.png"},
    "New Providence": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4013.png"},
    "Oratory": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6216.png"},
    "Plainfield": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4311.png"},
    "Rahway": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4349.png"},
    "Roselle Park": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4457.png"},
    "Scotch Plains-Fanwood": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4500.png"},
    "Summit": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4611.png"},
    "Union": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4710.png"},
    "Union Catholic": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/6208.png"},
    "Westfield": {"div": "UCC", "mascot": "", "p": "#1a2a4a", "s": "#2a4a7a", "t": "#8aaccc", "bg": "#060d18", "logo": "https://nj.vsand-static.com/Logos/4870.png"},
}

# ── SCRAPER ────────────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return r.read().decode("utf-8")

def fetch_stats(slug):
    return fetch(f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}/stats")

def fetch_schedule(slug):
    return fetch(f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}")

def parse_schedule(html):
    """Parse schedule page → {coach, wins, losses, games: [{date, opponent, result, score, home}]}"""
    # Head coach
    coach_match = re.search(r'Head Coach:\s*([A-Z][a-zA-Z\'\-]+(?: [A-Z][a-zA-Z\'\-]+)+)', html)
    coach = coach_match.group(1).strip() if coach_match else ""

    games = []
    tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
    if not tables:
        return {"coach": coach, "wins": 0, "losses": 0, "games": []}

    rows = re.findall(r'<tr.*?</tr>', tables[0], re.DOTALL)
    wins = losses = 0

    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        cells = [re.sub(r'&amp;', '&', c) for c in cells]
        cells = [re.sub(r'&#x27;', "'", c) for c in cells]
        cells = [re.sub(r'&[a-z]+;', '', c) for c in cells]
        cells = [re.sub(r'<[^>]+>', ' ', c) for c in cells]
        cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
        cells = [c for c in cells if c and c != '\xa0']

        if len(cells) < 3 or cells[0] == 'Date':
            continue

        date     = cells[0] if len(cells) > 0 else ""
        opponent = cells[1] if len(cells) > 1 else ""
        result   = cells[2] if len(cells) > 2 else ""

        # Clean opponent (strip tournament info after comma)
        opp_clean = opponent.split(',')[0].strip()
        home = not opp_clean.startswith('@')
        opp_clean = opp_clean.lstrip('vs@ ').strip()

        # Parse result: "W 11-1" or "L 6-1"
        outcome = ""
        score   = ""
        rm = re.match(r'([WL])\s+(\d+-\d+)', result)
        if rm:
            outcome = rm.group(1)
            score   = rm.group(2)
            if outcome == 'W': wins += 1
            else: losses += 1

        if date and opp_clean:
            games.append({
                "date":     date,
                "opponent": opp_clean,
                "home":     home,
                "outcome":  outcome,
                "score":    score,
            })

    return {"coach": coach, "wins": wins, "losses": losses, "games": games}

def get_table_rows(html):
    """Return list of tables, each a list of rows, each a list of cell strings."""
    tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
    result = []
    for t in tables:
        rows = re.findall(r'<tr.*?</tr>', t, re.DOTALL)
        parsed_rows = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', ' ', c) for c in cells]
            cells = [re.sub(r'&bull;', '•', c) for c in cells]
            cells = [re.sub(r'&mdash;', '0', c) for c in cells]
            cells = [re.sub(r'&[a-z]+;', '', c) for c in cells]
            cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
            if any(c for c in cells):
                parsed_rows.append(cells)
        result.append(parsed_rows)
    return result

def clean_cell(cell):
    cell = re.sub(r'<[^>]+>', ' ', cell)
    cell = unescape(cell).replace('\xa0', ' ')
    cell = re.sub(r'&bull;', '•', cell)
    cell = re.sub(r'&mdash;', '0', cell)
    cell = re.sub(r'\s+', ' ', cell).strip()
    return cell

def get_table_rows_from_table(table_html):
    rows = []
    for row in re.findall(r'<tr.*?</tr>', table_html, re.DOTALL | re.I):
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.I)
        cells = [clean_cell(c) for c in cells]
        if any(cells):
            rows.append(cells)
    return rows

def extract_player_links(stats_html):
    links = {}
    for href, name in re.findall(r'<a\s+href="(/player/[^"]+/baseball/season/[^"]+)">([^<]+)</a>', stats_html, re.I):
        clean_name = clean_cell(name)
        if clean_name:
            links.setdefault(clean_name, href)
    return links

def parse_name_pos_year(cell):
    """Parse 'Jordan Jackson #8 • Senior • OF, P' -> (name, pos, year)"""
    cell = re.sub(r'#\d+', '', cell)
    cell = re.sub(r'&bull;', '•', cell)
    parts = [p.strip() for p in cell.split('•') if p.strip()]
    name = parts[0].strip() if len(parts) > 0 else cell.strip()
    year = parts[1].strip() if len(parts) > 1 else ''
    pos  = parts[2].strip() if len(parts) > 2 else ''
    name = re.sub(r'\s+(?:#|/)\d+\s*$', '', name).strip()

    grade_match = re.search(r'\s+(Freshman|Sophomore|Junior|Senior)$', name, re.I)
    if grade_match:
        grade = grade_match.group(1).title()
        name = name[:grade_match.start()].strip()
        if year.title() not in {'Freshman', 'Sophomore', 'Junior', 'Senior'}:
            if year and not pos:
                pos = year
            year = grade

    if year.title() in {'Freshman', 'Sophomore', 'Junior', 'Senior'}:
        year = year.title()
    return name, pos, year

def parse_player_game_logs(profile_html):
    logs = {}
    tables = re.findall(r'<table.*?</table>', profile_html, re.DOTALL | re.I)
    for table in tables:
        rows = get_table_rows_from_table(table)
        if len(rows) < 2:
            continue
        header = rows[0]
        is_game_log = len(header) >= 3 and header[0] == 'Date' and header[1] == 'Opponent' and header[2] == 'Result'
        if not is_game_log:
            continue

        if 'AB' in header and 'SLG' in header:
            parsed = []
            for row in rows[1:]:
                if len(row) < len(header):
                    row += [''] * (len(header) - len(row))
                if 'total' in row[0].lower():
                    continue
                parsed.append({
                    "date": row[0],
                    "opp": row[1],
                    "res": row[2],
                    "AB": row[3],
                    "R": row[4],
                    "H": row[5],
                    "RBI": row[6],
                    "B1": row[7],
                    "B2": row[8],
                    "B3": row[9],
                    "HR": row[10],
                    "BB": row[11],
                    "HBP": row[12],
                    "SB": row[13],
                    "AVG": row[19] if len(row) > 19 else "",
                    "SLG": row[20] if len(row) > 20 else "",
                })
            logs["hitting"] = parsed

        elif 'IP' in header and 'ERA' in header and 'PIT' in header:
            parsed = []
            for row in rows[1:]:
                if len(row) < len(header):
                    row += [''] * (len(header) - len(row))
                if 'total' in row[0].lower():
                    continue
                parsed.append({
                    "date": row[0],
                    "opp": row[1],
                    "res": row[2],
                    "W": row[3],
                    "L": row[4],
                    "PIT": row[5],
                    "IP": row[6],
                    "H": row[7],
                    "R": row[8],
                    "ER": row[9],
                    "BB": row[10],
                    "K": row[11],
                    "HB": row[12],
                    "ERA": row[14] if len(row) > 14 else "",
                })
            logs["pitching"] = parsed
    return logs

def safe_float(v, default=0.0):
    try:
        v = str(v).replace(',', '').strip()
        return float(v) if v else default
    except:
        return default

# ── HITTING PARSER ─────────────────────────────────────────────────────────────
# Columns: name | AB R H RBI 1B 2B 3B HR BB HBP SB SF SH/B ROE LOB FC AVG SLG
def parse_hitting(rows, team_name):
    players = []
    # Find header row
    header_idx = None
    for i, row in enumerate(rows):
        if 'AB' in row and 'RBI' in row:
            header_idx = i
            break
    if header_idx is None:
        return players

    for row in rows[header_idx + 1:]:
        if len(row) < 10:
            continue
        name, pos, year = parse_name_pos_year(row[0])
        if not name or 'total' in name.lower():
            continue

        AB  = safe_float(row[1])
        R   = safe_float(row[2])
        H   = safe_float(row[3])
        RBI = safe_float(row[4])
        B1  = safe_float(row[5])
        B2  = safe_float(row[6])
        B3  = safe_float(row[7])
        HR  = safe_float(row[8])
        BB  = safe_float(row[9])
        HBP = safe_float(row[10]) if len(row) > 10 else 0
        SB  = safe_float(row[11]) if len(row) > 11 else 0
        SF  = safe_float(row[12]) if len(row) > 12 else 0
        SH  = safe_float(row[13]) if len(row) > 13 else 0

        PA = AB + BB + HBP + SF + SH
        if PA == 0:
            continue

        AVG      = H / AB if AB > 0 else 0
        SLG      = (B1 + 2*B2 + 3*B3 + 4*HR) / AB if AB > 0 else 0
        OBP      = (H + BB + HBP) / (AB + BB + HBP + SF) if (AB + BB + HBP + SF) > 0 else 0
        OPS      = OBP + SLG
        ISO      = SLG - AVG
        BB_pct   = (BB / PA) * 100
        BsR      = (SB * 0.2) + (B3 * 0.1)
        wOBA     = ((0.7*(BB+HBP)) + (0.9*B1) + (1.3*B2) + (1.6*B3) + (2*HR)) / PA
        wRAA     = ((wOBA - WOBA_LEAGUE) / WOBA_SCALE) * PA
        wRC      = wRAA + (PA * R_PA_LEAGUE)
        wRC_plus = round(((wOBA - WOBA_LEAGUE) / WOBA_SCALE + R_PA_LEAGUE) / R_PA_LEAGUE * 100)
        OFF      = wRAA + BsR

        players.append({
            "name": name, "pos": pos, "year": year, "team": team_name,
            "PA": int(PA), "AB": int(AB), "R": int(R), "H": int(H), "RBI": int(RBI),
            "B1": int(B1), "B2": int(B2), "B3": int(B3), "HR": int(HR),
            "BB": int(BB), "HBP": int(HBP), "SB": int(SB),
            "AVG":     round(AVG, 3),
            "SLG":     round(SLG, 3),
            "OBP":     round(OBP, 3),
            "OPS":     round(OPS, 3),
            "ISO":     round(ISO, 3),
            "BB_pct":  round(BB_pct, 1),
            "BsR":     round(BsR, 2),
            "wOBA":    round(wOBA, 3),
            "wRAA":    round(wRAA, 2),
            "wRC":     round(wRC, 1),
            "wRC_plus":wRC_plus,
            "OFF":     round(OFF, 2),
            "qualified": PA >= 50
        })
    return players

# ── PITCHING PARSER ────────────────────────────────────────────────────────────
# Columns: name | W L PIT IP H R ER BB K HB PO ERA
def parse_pitching(rows, team_name):
    pitchers = []
    header_idx = None
    for i, row in enumerate(rows):
        if 'ERA' in row and 'IP' in row:
            header_idx = i
            break
    if header_idx is None:
        return pitchers

    for row in rows[header_idx + 1:]:
        if len(row) < 8:
            continue
        name, pos, year = parse_name_pos_year(row[0])
        if not name or 'total' in name.lower():
            continue

        W      = safe_float(row[1])
        L      = safe_float(row[2])
        # row[3] = PIT pitch count
        IP_str = row[4]
        ip_parts = IP_str.split('.')
        try:
            IP = int(ip_parts[0]) + (int(ip_parts[1]) / 3 if len(ip_parts) > 1 and ip_parts[1] else 0)
        except:
            continue
        if IP == 0:
            continue

        H  = safe_float(row[5])
        R  = safe_float(row[6])
        ER = safe_float(row[7])
        BB = safe_float(row[8])  if len(row) > 8  else 0
        K  = safe_float(row[9])  if len(row) > 9  else 0
        HB = safe_float(row[10]) if len(row) > 10 else 0

        ERA       = (ER / IP) * 7
        WHIP      = (BB + H) / IP
        K7        = (K / IP) * 7
        BB7       = (BB / IP) * 7
        KBB       = K / BB if BB > 0 else 999
        FIP_const = 3.10
        FIP       = ((3*(BB+HB) - 2*K) / IP) + FIP_const
        ERA_minus = round((ERA / 3.00) * 100)
        FIP_minus = round((FIP / 4.31) * 100)
        RAA       = ((3.00 - ERA) / 7) * IP
        WAR       = round(RAA / 10, 1)

        pitchers.append({
            "name": name, "pos": pos, "year": year, "team": team_name,
            "W": int(W), "L": int(L),
            "IP":        round(IP, 2),
            "H":         int(H), "R": int(R), "ER": int(ER),
            "BB":        int(BB), "K": int(K), "HB": int(HB),
            "ERA":       round(ERA, 2),
            "ERA_minus": ERA_minus,
            "FIP":       round(FIP, 2),
            "FIP_minus": FIP_minus,
            "WHIP":      round(WHIP, 2),
            "K7":        round(K7, 2),
            "BB7":       round(BB7, 2),
            "KBB":       round(KBB, 2) if KBB != 999 else 999,
            "RAA":       round(RAA, 1),
            "WAR":       WAR,
            "PIP":       0,
            "qualPitch": IP >= 15
        })
    return pitchers

# ── MAIN ───────────────────────────────────────────────────────────────────────
def scrape_team(display_name, slug):
    print(f"  Scraping {display_name} ({slug})...", end=" ", flush=True)
    try:
        stats_html = fetch_stats(slug)
        tables     = get_table_rows(stats_html)
        hitters    = parse_hitting(tables[0],  display_name) if len(tables) > 0 else []
        pitchers   = parse_pitching(tables[1], display_name) if len(tables) > 1 else []
        player_links = extract_player_links(stats_html)
        player_logs = {}
        for player_name in sorted({p["name"] for p in hitters + pitchers}):
            href = player_links.get(player_name)
            if not href:
                continue
            try:
                logs = parse_player_game_logs(fetch("https://highschoolsports.nj.com" + href))
                if logs:
                    player_logs[f"{display_name}::{player_name}"] = logs
            except Exception:
                pass
            time.sleep(0.05)

        sched_html = fetch_schedule(slug)
        schedule   = parse_schedule(sched_html)

        print(f"{len(hitters)} hitters, {len(pitchers)} pitchers, {len(player_logs)} logs, {schedule['wins']}-{schedule['losses']}")
        return hitters, pitchers, schedule, player_logs
    except Exception as e:
        print(f"ERROR: {e}")
        return [], [], {"coach": "", "wins": 0, "losses": 0, "games": []}, {}

def generate_js(all_hitters, all_pitchers, all_schedules={}, all_player_logs={}):
    """Write scraped data directly into js/data.js so the site updates immediately."""
    import os
    js_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js")
    out_path = os.path.join(js_dir, "data.js")
    logs_path = os.path.join(js_dir, "player_logs.js")

    now = __import__('datetime').datetime.now().strftime('%b %d, %Y')
    lines = [
        "// AUTO-GENERATED by scraper.py\n",
        f"// Last updated: {now}\n",
        "// Do not edit by hand — run: python3 scraper.py\n\n",
        f"const DATA_UPDATED = '{now}';\n\n",
    ]

    # Team identity
    lines.append("const TM = {\n")
    for team in TEAMS:
        meta = dict(TEAM_META.get(team, {}))
        meta.setdefault("div", "")
        meta.setdefault("mascot", "")
        meta.setdefault("p", "#1a2a4a")
        meta.setdefault("s", "#2a4a7a")
        meta.setdefault("t", "#8aaccc")
        meta.setdefault("bg", "#060d18")
        meta.setdefault("logo", "")
        lines.append(f"  {json.dumps(team)}: {json.dumps(meta)},\n")
    lines.append("};\n\n")

    # Stat configs
    lines.append("""const HSC = {
  AVG:     { label:'AVG',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  SLG:     { label:'SLG',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  OBP:     { label:'OBP',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  OPS:     { label:'OPS',  fmt: v => v.toFixed(3) },
  BsR:     { label:'BsR',  fmt: v => v.toFixed(1) },
  ISO:     { label:'ISO',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  BB_pct:  { label:'BB%',  fmt: v => v.toFixed(1)+'%' },
  wOBA:    { label:'wOBA', fmt: v => v.toFixed(3).replace(/^0/,'') },
  wRAA:    { label:'wRAA', fmt: v => v.toFixed(1) },
  wRC:     { label:'wRC',  fmt: v => v.toFixed(0) },
  wRC_plus:{ label:'wRC+', fmt: v => v.toFixed(0) },
  OFF:     { label:'OFF',  fmt: v => v.toFixed(1) }
};
const HIT_TABLE_COLS = ['wRC_plus','wOBA','OPS','AVG','SLG','OBP','ISO','BsR','OFF'];
const HIT_PCT_GROUPS = [
  { title:'Advanced Rate', stats:['wRC_plus','wRC','wOBA','wRAA'] },
  { title:'Traditional',   stats:['OPS','OBP','SLG','AVG'] },
  { title:'Other',         stats:['ISO','BB_pct','BsR','OFF'] }
];\n\n""")

    lines.append("""const PSC = {
  IP:       { label:'IP',   fmt: v => v.toFixed(1),  lowerBetter:false },
  H:        { label:'H',    fmt: v => v.toFixed(0),  lowerBetter:true  },
  R:        { label:'R',    fmt: v => v.toFixed(0),  lowerBetter:true  },
  ER:       { label:'ER',   fmt: v => v.toFixed(0),  lowerBetter:true  },
  BB:       { label:'BB',   fmt: v => v.toFixed(0),  lowerBetter:true  },
  K:        { label:'K',    fmt: v => v.toFixed(0),  lowerBetter:false },
  HB:       { label:'HB',   fmt: v => v.toFixed(0),  lowerBetter:true  },
  ERA:      { label:'ERA',  fmt: v => v.toFixed(2),  lowerBetter:true  },
  ERA_minus:{ label:'ERA-', fmt: v => v.toFixed(0),  lowerBetter:true  },
  FIP:      { label:'FIP',  fmt: v => v.toFixed(2),  lowerBetter:true  },
  FIP_minus:{ label:'FIP-', fmt: v => v.toFixed(0),  lowerBetter:true  },
  RAA:      { label:'RAA',  fmt: v => v.toFixed(1),  lowerBetter:false },
  K7:       { label:'K/7',  fmt: v => v.toFixed(2),  lowerBetter:false },
  BB7:      { label:'BB/7', fmt: v => v.toFixed(2),  lowerBetter:true  },
  PIP:      { label:'P/IP', fmt: v => v.toFixed(1),  lowerBetter:false },
  KBB:      { label:'K/BB', fmt: v => v.toFixed(2),  lowerBetter:false },
  WHIP:     { label:'WHIP', fmt: v => v.toFixed(2),  lowerBetter:true  },
  WAR:      { label:'WAR',  fmt: v => v.toFixed(1),  lowerBetter:false }
};
const PIT_TABLE_COLS = ['ERA','FIP','WHIP','K7','BB7','KBB','ERA_minus','FIP_minus','WAR','IP'];
const PIT_PCT_GROUPS = [
  { title:'Run Prevention',  stats:['ERA','ERA_minus','FIP','FIP_minus'] },
  { title:'Command & Stuff', stats:['WHIP','K7','BB7','KBB'] },
  { title:'Value',           stats:['WAR','RAA','IP','K'] }
];\n\n""")

    # Hitters array
    lines.append("const AP = [\n")
    for p in all_hitters:
        lines.append(f"  {json.dumps(p)},\n")
    lines.append("];\n\n")

    # Pitchers array
    lines.append("const PP = [\n")
    for p in all_pitchers:
        lines.append(f"  {json.dumps(p)},\n")
    lines.append("];\n\n")

    # Schedules object
    lines.append("const SCHEDULES = {\n")
    for team, sched in all_schedules.items():
        lines.append(f"  {json.dumps(team)}: {json.dumps(sched)},\n")
    lines.append("};\n")

    with open(out_path, "w") as f:
        f.writelines(lines)

    print(f"\n✅  Written to {out_path}")
    log_lines = [
        "// AUTO-GENERATED game logs from NJ.com player pages\n",
        "// Loaded lazily by js/app.js\n",
        "const PLAYER_LOGS = {\n",
    ]
    for key, logs in sorted(all_player_logs.items()):
        log_lines.append(f"  {json.dumps(key)}: {json.dumps(logs)},\n")
    log_lines.append("};\n")
    with open(logs_path, "w") as f:
        f.writelines(log_lines)
    print(f"✅  Written to {logs_path}")
    return out_path

def print_summary(all_hitters, all_pitchers):
    print(f"\n{'─'*50}")
    print(f"  Total hitters:  {len(all_hitters)}")
    print(f"  Total pitchers: {len(all_pitchers)}")
    teams = sorted(set(p['team'] for p in all_hitters))
    print(f"  Teams scraped:  {', '.join(teams)}")

    # Top 5 hitters by wRC+
    print(f"\n  Top 5 by wRC+ (qualified):")
    qualified = [p for p in all_hitters if p['qualified']]
    for p in sorted(qualified, key=lambda x: x['wRC_plus'], reverse=True)[:5]:
        print(f"    {p['name']:25} {p['team']:15} wRC+: {p['wRC_plus']}")

    # Top 5 pitchers by ERA
    print(f"\n  Top 5 ERA (qualified):")
    qpit = [p for p in all_pitchers if p['qualPitch']]
    for p in sorted(qpit, key=lambda x: x['ERA'])[:5]:
        print(f"    {p['name']:25} {p['team']:15} ERA: {p['ERA']:.2f}")
    print(f"{'─'*50}\n")

if __name__ == "__main__":
    # Allow scraping a single team via CLI arg
    if len(sys.argv) > 1:
        slug = sys.argv[1]
        name = slug.replace('-', ' ').title()
        teams_to_scrape = {name: slug}
    else:
        teams_to_scrape = TEAMS

    print(f"\n🔍 Scraping {len(teams_to_scrape)} team(s) from highschoolsports.nj.com...\n")

    all_hitters   = []
    all_pitchers  = []
    all_schedules = {}
    all_player_logs = {}

    for display_name, slug in teams_to_scrape.items():
        hitters, pitchers, schedule, player_logs = scrape_team(display_name, slug)
        all_hitters.extend(hitters)
        all_pitchers.extend(pitchers)
        all_schedules[display_name] = schedule
        all_player_logs.update(player_logs)
        time.sleep(0.5)  # be polite to the server

    print_summary(all_hitters, all_pitchers)
    generate_js(all_hitters, all_pitchers, all_schedules, all_player_logs)
