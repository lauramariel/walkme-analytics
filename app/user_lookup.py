from google.cloud import firestore
from config import logger

DB = firestore.Client(project="nutanix-testdrive-10")


def lookup_user_by_id(ds, id):
    marketoid = "_User__marketo_id"
    email = ""
    user_obj = DB.collection("produser").where(marketoid, "==", id).stream()
    for user_doc in user_obj:
        # user_doc always exists even if it's empty
        # it just returns null if it can't find it
        email = user_doc.to_dict()["_User__email"]
        logger.info(f"Email lookup returned: {email}")

    if len(email) <= 0:
        logger.info("Marketo ID not found in prod db, check staging db")
        # check stageuser
        user_obj = DB.collection("stageuser").where(marketoid, "==", id).stream()
        for user_doc in user_obj:
            email = user_doc.to_dict()["_User__email"]

    # return email or empty string
    return email
