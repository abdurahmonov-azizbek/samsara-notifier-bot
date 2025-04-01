import asyncio
from src.api.api import SamsaraClient

client = SamsaraClient("samsara_api_iQ9uNP0KqJfP3oEx1yI9LMBZFKign6")

async def main():
    result = await client.get_all_trucks()
    # for truck in result:
    #     count = 0
    #     for truck2 in result:
    #         if truck2["name"] == truck["name"]:
    #             count += 1
    #     if count != 1:
    #         print("Takrorlangan: ", truck["name"], truck["id"])
    # print(result[0])

    details = await client.get_truck_details(281474979251985) # 130 truck
    print(details)

if __name__ == "__main__":
    asyncio.run(main())