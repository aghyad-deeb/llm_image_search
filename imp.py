from openai import OpenAI
from dotenv import load_dotenv
import time
import os
import requests
load_dotenv(override=True)

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
CSE_ID = os.environ["CSE_ID"]
client = OpenAI()


def image_search(query, trial=0):
    print(f"image_search({query=}, {trial=})")
    url = 'https://www.googleapis.com/customsearch/v1'
    num_res = 10 
    if trial == 0:
        start_dict = dict()
    else:
        start_dict = dict(start=trial*num_res + 1)
    params = {
        'q': query,
        'cx': CSE_ID,
        'key': GOOGLE_API_KEY,
        'searchType': 'image',
        'num': num_res,
        **start_dict
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CustomSearchClient/1.0)'
    }
    s = 429
    req_num = 0
    while s == 429:

        response = requests.get(url, params=params)
        s = response.status_code
        if response.status_code == 200:
            results = response.json().get('items', [])
            return results
        elif response.status_code == 429:
            print(f"Too many requests, waiting: {response.status_code}")
            time.sleep(10 + 2**req_num)
            return []


def get_query_from_model(image_desc):
    prompt = "The user wants an image with the following description: "\
            f"{image_desc}. What's a good query for a search engine to "\
            "ensure the user finds what they want? Output only the query "\
            "and nothing else."

    print(f"{prompt=}")
    response = client.responses.create(
        model="gpt-4o",
        input=prompt,
    )


    out_txt = response.output_text
    return out_txt


def check_image(link, image_desc):
    prompt = f"Does this image match the following description? {image_desc}"\
            "Output only a number between 0 and 100 representing how much the"\
            " image matches the description "
    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": link,
                    },
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                ],
            },
        ]
    )

    out_txt = response.output_text
    #if out_txt[0] == "1":
    #    return True
    #elif out_txt[0] == "0":
    #    return False
    #else:
    #    print("Unexpected Output when checking image: {out_txt=}")
    #    return False
    if out_txt[:2].isnumeric():
        return int(out_txt[:2])
    else:
        return -1

def process(image_desc, trial=0, thresh=80):
    query = get_query_from_model(image_desc)
    print(f"{query=}")
    images = []
    for i in range(50):
        images = image_search(query, trial=trial)
        if len(images) > 0:
            break
        time.sleep(5 + i)
    
    links = [image.get("link") for image in images]
    
    print("\nchecking_images")
    correct_images = list()
    for link in links:
        print(f"Processing {link=}")
        try:
            score = check_image(link, image_desc)
            if score > thresh:
                correct_images.append(link)
        except:
            print(f"Error. Skipping {link=}")

    print(f"Found {len(links)} images, accepted {len(correct_images)}.")
    return images, correct_images


def main():
    inp = input("describe your image: ") 
    dflt = "an image of a house kitchen where the camera is facing the counter of the kitchen with the microwave on the far left and the fridge on the far right. There's a wooden table in front of the counter top with chairs far enough from the table for someone to fit there."
    image_desc = inp if inp != "" else dflt
    correct_images = list()
    for i in range(50):
        images, correct_images_n = process(image_desc, trial=i)
        correct_images += correct_images_n
        if len(correct_images) > 5:
            break
        print(f"images={[image.get('link') for image in images]}")
        time.sleep(5)

    from PIL import Image
    for link in correct_images:
        image_data = requests.get(link, stream=True).raw
        image = Image.open(image_data)
        try:
            image.show()
        except:
            continue


if __name__ == "__main__":
    for trial in range(10):
        print(f"\n\n{trial=}\n", image_search('"house kitchen interior with microwave on left, fridge on right, wooden table with chairs in front of counter"', trial))
    #main()
