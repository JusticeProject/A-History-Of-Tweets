import os

output = open("output.html", "w")

for dirpath, dirnames, filenames in os.walk(r"..\output"):
    for filename in filenames:
        if ("Tweets" in filename) and (".txt") in filename:
            filepath = dirpath + "\\" + filename
            lines = open(filepath, "r", encoding="utf-8").readlines()
            for line in lines:
                if "gettr" in line.lower():
                    tweetID = line.split(",", 1)[0]
                    output.write('<a href="https://twitter.com/i/web/status/' + tweetID + '">Link</a>')
                    output.write('\n<br>\n<br>\n')
            
output.close()
