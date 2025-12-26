import json
f = open("game_object_weights.json")
weights = json.load(f)
f.close()
f = open("game_objects.json")
objects = json.load(f)
f.close()

for weight in weights:
    ss = weight["synset"]
    for object in objects:
        if ss==object["synset"]:
            print(ss, weight['weight'])
            object["weight"] = weight["weight"]
f = open("game_objects.json", "w")
json.dump(objects, f, indent=2)
