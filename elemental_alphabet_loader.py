import json

f = open("dark_alphabet.json","r",encoding="utf-8")

data = json.load(f)

set = {}
for key in data["elemental_morphemes"]:
    part = data["elemental_morphemes"][key]
    letters = part["morphemes"]
    set[key] = []
    val = 0
    for n in letters:
        val += 1
        n['value'] = val
        n['spelling'] = n['morpheme']
        del n['spelling']

        set[key].append(n)

print(set)
f = open("elemental_dark.json","w")
json.dump(set,f, indent = 4)