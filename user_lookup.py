from google.cloud import firestore

DB = firestore.Client(project="nutanix-testdrive-10")


def lookup_user_by_id(ds, id):
    marketoid = "_User__marketo_id"
    user_obj = DB.collection(ds + "user").where(marketoid, "==", id).stream()
    for user_doc in user_obj:
        # user_doc always exists even if it's empty
        # it just returns null if it can't find it
        email = user_doc.to_dict()["_User__email"]
        return email
