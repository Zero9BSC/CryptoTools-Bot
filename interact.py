from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

# Configuración del navegador
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')

# Inicialización del navegador
driver = webdriver.Chrome(chrome_options=options)

# Abrir la página
driver.get("https://fluxbeam.xyz/app/tools")

# Aquí puedes interactuar con la página usando Selenium, por ejemplo:
# Encontrar un elemento y hacer clic en él
# element = driver.find_element_by_xpath("XPATH_DEL_ELEMENTO")
# element.click()

# O rellenar un formulario
# input_box = driver.find_element_by_xpath("XPATH_DEL_INPUT")
# input_box.send_keys("Tu texto aquí")

# Pausar el script para ver el estado
time.sleep(10)

# Cerrar el navegador
driver.quit()
