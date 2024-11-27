import frappe
import requests
from bs4 import BeautifulSoup


def scrape_tracking_status(tracking_number):
	url = f"http://everest.cargotrack.net/m/track.asp?track={tracking_number}"

	response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

	if response.status_code == 200:
		soup = BeautifulSoup(response.content, 'html.parser')

		# Encontrar la tabla con clase 'ntextbig'
		table = soup.find('table', {'class': 'ntextbig'})

		if table:
			# Encontrar el tbody dentro de la tabla
			tbody = table.find('tbody')
			if tbody:
				# Encontrar todos los tr dentro del tbody
				rows = tbody.find_all('tr')

				# Verificar que hay al menos 3 tr
				if len(rows) >= 3:
					# Ignorar el primer y tercer tr, enfocarse en el segundo
					second_tr = rows[1]

					# Dentro del segundo tr, encontrar la etiqueta <strong>
					strong_tag = second_tr.find('strong')

					if strong_tag:
						# Extraer el texto dentro de <strong>
						status = strong_tag.get_text(strip=True)
						return status
					else:
						return 'No se encontró la etiqueta <strong> en el segundo tr.'
				else:
					return 'No hay suficientes filas en la tabla.'
			else:
				return 'No se encontró el tbody en la tabla.'
		else:
			return 'No se encontró la tabla con clase ntextbig.'
	else:
		return f'Error: Código de estado HTTP {response.status_code}'


@frappe.whitelist()
def get_tracking_status():
	# Obtener los Parcel en los estados indicados
	parcels = frappe.get_all('Parcel', filters={
		'status': ['in', ['Awaiting Receipt', 'Awaiting Confirmation']]
	}, fields=['name', 'tracking_number'])

	resultados = {}

	for parcel in parcels:
		# Verificar que el tracking_number no esté vacío
		# Realizar el scraping para obtener el estado
		status = scrape_tracking_status(parcel.tracking_number)

		# Guardar el resultado en el diccionario
		resultados[parcel.tracking_number] = status

		# Pausa de 3 segundos
		# time.sleep(0.5)

	# Retornar el diccionario de resultados
	return resultados
