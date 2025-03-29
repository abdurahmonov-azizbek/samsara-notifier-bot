from src.config import ADMIN_ID
from src import  db
from src.services import company_service, truck_service, notification_service, user_service
from src.api.api import SamsaraClient
from src import constants
from src.models import Truck, Company, Notification
from src.logger import logger
from src.base import bot
from src.api.api import SamsaraClient
from src.handlers.user_handler import fetch_truck_details
from datetime import  datetime

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


async def send_auto_notifications():
    try:
        query = """SELECT * 
            FROM notification
            WHERE notification_type_id = 3
            AND (
                last_send_time IS NULL 
                OR last_send_time + (every_minutes * INTERVAL '1 minute') <= NOW()
            );
            """

        notifications = await notification_service.get_by_query(query)

        for notification in notifications:
            truck = await truck_service.get_by_id(notification.truck_id, "truck_id")
            if not truck:
                logger.info(f"Truck not found in send_auto_notifications with id: {notification.truck_id}")
                continue
            company = await company_service.get_by_id(truck.company_id)
            if not company:
                logger.info(f"Company not found in send_auto_notifications with id: {truck.company_id}")
                continue

            await fetch_truck_details(bot, notification.telegram_id, notification.truck_id, company.api_key)
            newNotification = notification
            newNotification.last_send_time = datetime.now()
            await notification_service.update(newNotification)


    except Exception as e:
        logger.error(f"Error while sendint auto notifications: {e}")