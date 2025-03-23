from config import ADMIN_ID
import db
from services import company_service, truck_service
from api.api import SamsaraClient
import constants
from models import Truck

async def is_admin(user_id) -> bool:
    return user_id == ADMIN_ID

async def sync_trucks():
    companies = await company_service.get_all()

    for company in companies:
        api_key = company.api_key
        client = SamsaraClient(api_key)
        samsara_trucks = await client.get_all_trucks()

        if not samsara_trucks:
            continue

        # Fetch existing trucks for the company from our database
        existing_trucks = await truck_service.get_by_company_id(company.id)
        
        # Convert to dictionaries for fast lookup
        existing_trucks_dict = {truck.truck_id: truck for truck in existing_trucks}
        samsara_truck_ids = {int(truck["id"]) for truck in samsara_trucks}

        # Process Samsara trucks
        for truck in samsara_trucks:
            truck_id = int(truck["id"])  # Convert Samsara's ID to int
            truck_name = truck["name"]   # Get Samsara's truck name

            if truck_id not in existing_trucks_dict:
                # Insert new truck
                new_truck = Truck(
                    id=None,  # Auto-increment in DB
                    name=truck_name,
                    truck_id=truck_id,
                    company_id=company.id
                )
                await truck_service.create(new_truck)
            else:
                # Update truck name if it has changed
                existing_truck = existing_trucks_dict[truck_id]
                if existing_truck.name != truck_name:
                    existing_truck.name = truck_name
                    await truck_service.update(existing_truck)

        trucks_to_delete = [
            truck for truck_id, truck in existing_trucks_dict.items() if truck_id not in samsara_truck_ids
        ]

        for truck in trucks_to_delete:
            await truck_service.delete(truck.id)
