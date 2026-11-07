import hashlib
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from news_service import fetch_job_scam_news

if not firebase_admin._apps: #intialize firebase admin sdk
    firebase_credentials=os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if firebase_credentials:
        cred=credentials.Certificate(json.loads(firebase_credentials))
    else:
        cred=credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db=firestore.client() #connect to firestore

def update_news():
    print("Searching for Malyasian job scam news...")
    articles=fetch_job_scam_news(max_articles=30) #retrieve articles
    if not articles:
        print("No new relevant articles retrieved.")
        return
    collection=db.collection("job_scam_news") #saved here
    for article in articles:
        url=article["url"]
        document_id=hashlib.sha256(url.encode("utf-8")).hexdigest()
        article["updated_at"]=firestore.SERVER_TIMESTAMP #store record in firestore only
        collection.document(document_id).set(article)
    print(f"Retrieved and saved {len(articles)} articles.")
    documents=list(collection.stream()) #retrieve all stored articles
    documents.sort(
        key=lambda doc:doc.to_dict().get("published_at",""),
        reverse=True
    )
    old_documents=documents[30:] #delete old articles
    batch=db.batch()
    for document in old_documents:
        batch.delete(document.reference)
    if old_documents:
        batch.commit()
    print(f"Removed {len(old_documents)} older articles.")
    print("Firestore news update completed!")

if __name__=="__main__":
    update_news()