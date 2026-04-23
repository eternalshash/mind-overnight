library(worldfootballR)

print("Loading Match Details for EPL...")

# This pulls the massive dataset containing lineups, stats, and match ratings
epl_match_details <- load_fotmob_match_details(
  country = "ENG", 
  league_name = "Premier League"
)

# Export straight to CSV so we can jump into Python
write.csv(epl_match_details, "epl_match_details.csv", row.names = FALSE)

print("Match data exported successfully! Ready for Python.")
