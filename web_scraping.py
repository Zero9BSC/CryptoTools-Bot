import requests
from bs4 import BeautifulSoup

# URL de la página
url = 'https://fluxbeam.xyz/app/tools/token_create'

# Realiza una solicitud GET a la página
response = requests.get(url)

# Verifica si la solicitud fue exitosa
if response.status_code == 200:
    # Parsea el contenido HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Imprime todo el contenido HTML
    print(soup.prettify())
else:
    print('Error al acceder a la página')
