import openai
from astrapy import DataAPIClient
import numpy as np
from sklearn.decomposition import PCA
import json
import os
import dotenv

# Initialize the client with your AstraDB token
client = DataAPIClient(api_key=os.getenv('OPENAI_API_KEY'))

openai.api_key = os.getenv('ASTRADB_API_KEY')

# Connect to the database
db = client.get_database_by_api_endpoint(
        "https://42fb8d5a-7632-4a0b-b02e-2b39238e3d06-us-east-2.apps.astra.datastax.com"
)

# Specify the collection (like a table in SQL)
collection_name = "structuredjson24"

# Load your JSON data
json_data = {
    "organization": "Connected Nation",
    "location": "Bowling Green, Kentucky",
    "mission": "Expanding access, adoption, and use of broadband to all people.",
    "about": {
      "overview": "Connected Nation is a national nonprofit that has worked in the broadband and related technology space for more than 20 years.",
      "belief": "Everyone should have the opportunity to use technology to improve their lives, families, and communities.",
      "operations": "We work at the community, state, and federal levels with both public and private partners."
    },
    "impact": {
      "low_income_families_without_broadband": "43%",
      "tribal_residents_without_broadband": "13.23%",
      "school_aged_children_without_broadband": "16.9 million"
    },
    "history": {
      "founding_date": "2001",
      "20_years_celebration": "November 17, 2021",
      "event_details": "Hosted a live event aired nationally from three U.S. cities."
    },
    "services": {
      "assessment_and_planning": "Developing public-private partnerships to bring technology access to targeted geographies and populations.",
      "education_and_empowerment": "Developing programs focused on technology skills and resources to improve quality of life."
    },
    "governance": {
      "board_of_directors": "Provides strategic and comprehensive oversight.",
      "advisors": "Includes elected officials, educators, healthcare representatives, and business leaders."
    },
    "relationship_with_providers": "Neutral party working with any broadband service providers.",
    "funding_sources": ["Foundations", "State and federal grants", "Local community contributions"],
    "glossary": {
      "3G": "3rd generation wireless telecommunications standards usually with network speeds of less than 1 Mbps.",
      "4G": "4th generation wireless telecommunications standards usually with network speeds greater than 1 Mbps.",
      "5G": "Emerging 5th generation wireless telecommunications standards usually associated with network speeds up to 1 Gbps or more.",
      "asymmetrical_connection": "A connection in which the maximum transfer rate is different for download and upload speeds.",
      "backbone": "A major high-speed transmission line that links smaller high-speed internet networks globally.",
      "bit": "The base unit of information in computing and the base unit of measuring network speeds.",
      "broadband": "High-speed internet access that is always on and faster than dial-up access.",
      "broadband_adoption": "The use of broadband where it is available, measured as the percentage of households using broadband.",
      "cable_modem": "Internet access provided by cable television companies using a shared neighborhood connection.",
      "central_office": "A telecommunication company’s building where consumer phone lines connect to the network.",
      "community_anchor_institution": "Organizations providing outreach, access, and support services to facilitate broadband use.",
      "conduit": "A reinforced tube protecting fiber-optic cables.",
      "dark_fiber": "Fiber that is in place but not being used for broadband services.",
      "digital_divide": "The gap between those with internet access and those without.",
      "digital_equity": "Ensuring access to robust broadband connections, internet-enabled devices, and skills for digital participation.",
      "digital_literacy": "The ability to use technology effectively for research, content creation, and interaction.",
      "dsl": "A technology that allows simultaneous internet and telephone network use over a two-wire copper line.",
      "e-government": "Government use of web-based resources to provide online services and connect with citizens.",
      "fiber_optic": "A glass or plastic strand capable of transmitting large amounts of data at high transfer rates."
    }
  }

# Concatenate text fields for embedding
text_to_vectorize = " ".join([
    json_data["mission"],
    json_data["about"]["overview"],
    json_data["about"]["belief"],
    json_data["about"]["operations"]
])

# Generate embedding using OpenAI's text-embedding-3-large (8192-dimension)
response = openai.embeddings.create(
    input=[text_to_vectorize],  # OpenAI now expects a list for batch processing
    model="text-embedding-3-large"
)

# Extract the 8192-dimension embedding as a NumPy array
vector_embedding = np.array(response.data[0].embedding)

# Reduce dimensions using PCA to AstraDB's 1000-dimension limit
target_dims = 1000  # AstraDB's vector limit
pca = PCA(n_components=target_dims)
vector_embedding_reduced = pca.fit_transform(vector_embedding.reshape(1, -1)).flatten().tolist()

# Add reduced vector to JSON
json_data["vector_embedding"] = vector_embedding_reduced

# Insert the JSON data into the collection
#db.get_collection(collection_name).delete_all()
inserted_document = db.get_collection(collection_name).insert_one(json_data)