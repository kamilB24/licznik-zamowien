import streamlit as st
import json
import base64
import requests
import os
from collections import Counter
from datetime import datetime, timedelta
import pytz

# -------------------------------
# Konfiguracja Streamlit
# -------------------------------
st.set_page_config(
    page_title="Licznik zamówień",
    page_icon="📦",
    layout="centered"
)

# -------------------------------
# Funkcje pomocnicze (zachowane z oryginalnej aplikacji)
# -------------------------------

def get_token(auth_code, client_id, client_secret, base_url):
    """Uzyskanie tokenu przy użyciu kodu autoryzacyjnego."""
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded}"
    }
    auth_params = {
        "grantType": "authorization_code",
        "token": auth_code
    }
    if not base_url.endswith('/'):
        base_url += "/"
    
    try:
        response = requests.post(base_url + "rest/auth/token/", headers=headers, json=auth_params)
        if response.status_code in range(200, 299):
            return response.json()
        else:
            return None
    except:
        return None

def connection_test(auth_token, base_url):
    """Sprawdzenie poprawności połączenia."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    if not base_url.endswith('/'):
        base_url += "/"
    
    try:
        req = requests.get(base_url + "rest/api/", headers=headers)
        if req.status_code == 200:
            return req.json()
        else:
            return None
    except:
        return None

def get_all_orders(auth_token, base_url):
    """Pobiera wszystkie zamówienia z ostatnich 5 dni."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    all_orders = []
    limit = 512
    offset = 0
    five_days_ago = datetime.now().astimezone() - timedelta(days=5)
    
    if not base_url.endswith('/'):
        base_url += "/"

    while True:
        url = base_url + "rest/api/orders/"
        params = {
            "limit": limit,
            "offset": offset,
            "updatedAfter": five_days_ago.isoformat()
        }
        try:
            req = requests.get(url, headers=headers, params=params)
            if req.status_code == 200:
                data_resp = req.json()
                orders_batch = data_resp.get("orders", [])
                all_orders.extend(orders_batch)
                total_count = data_resp.get("totalCount", len(orders_batch))
                if offset + len(orders_batch) >= total_count:
                    break
                offset += limit
            else:
                break
        except:
            break
    return {"orders": all_orders}

# -------------------------------
# Funkcje do zarządzania danymi autoryzacyjnymi
# -------------------------------

def save_auth_data(base_url, access_token, refresh_token):
    """Zapisuje dane autoryzacyjne w session_state."""
    st.session_state.auth_data = {
        "base_url": base_url,
        "access_token": access_token,
        "refresh_token": refresh_token
    }

def get_auth_data():
    """Pobiera dane autoryzacyjne z session_state."""
    return st.session_state.get('auth_data', None)

def clear_auth_data():
    """Usuwa dane autoryzacyjne."""
    if 'auth_data' in st.session_state:
        del st.session_state.auth_data

# -------------------------------
# Interfejs autoryzacji
# -------------------------------

def show_auth_form():
    """Pokazuje formularz autoryzacji."""
    st.title("🔐 Autoryzacja")
    
    auth_method = st.radio(
        "Wybierz metodę autoryzacji:",
        ["Kod autoryzacyjny", "Bezpośrednio tokeny"]
    )
    
    if auth_method == "Kod autoryzacyjny":
        with st.form("auth_code_form"):
            base_url = st.text_input("Adres API URL:", placeholder="https://twoja-domena.apilo.com")
            auth_code = st.text_input("Kod autoryzacyjny:", type="password")
            client_id = st.text_input("ID klienta:")
            client_secret = st.text_input("Sekretny klucz:", type="password")
            
            if st.form_submit_button("Połącz"):
                if base_url and auth_code and client_id and client_secret:
                    with st.spinner("Łączenie..."):
                        token_data = get_token(auth_code, client_id, client_secret, base_url)
                        if token_data and 'accessToken' in token_data:
                            if connection_test(token_data['accessToken'], base_url):
                                save_auth_data(
                                    base_url,
                                    token_data['accessToken'],
                                    token_data.get('refreshToken', "")
                                )
                                st.success("✅ Połączenie nawiązane pomyślnie!")
                                st.rerun()
                            else:
                                st.error("❌ Nie udało się nawiązać połączenia.")
                        else:
                            st.error("❌ Nie udało się uzyskać tokenu.")
                else:
                    st.error("Wypełnij wszystkie pola!")
    
    else:  # Bezpośrednio tokeny
        with st.form("direct_tokens_form"):
            base_url = st.text_input("Adres API URL:", placeholder="https://twoja-domena.apilo.com")
            access_token = st.text_input("Access Token:", type="password")
            refresh_token = st.text_input("Refresh Token:", type="password")
            
            if st.form_submit_button("Połącz"):
                if base_url and access_token:
                    with st.spinner("Sprawdzanie połączenia..."):
                        if connection_test(access_token, base_url):
                            save_auth_data(base_url, access_token, refresh_token)
                            st.success("✅ Połączenie nawiązane pomyślnie!")
                            st.rerun()
                        else:
                            st.error("❌ Nie udało się nawiązać połączenia.")
                else:
                    st.error("Wypełnij przynajmniej adres API i Access Token!")

# -------------------------------
# Główny interfejs aplikacji
# -------------------------------

def show_main_app():
    """Pokazuje główny interfejs aplikacji."""
    auth_data = get_auth_data()
    
    # Nagłówek
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📦 Licznik zamówień")
    
    # Przyciski
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Odśwież dane", type="primary"):
            st.rerun()
    
    with col2:
        if st.button("🚪 Wyloguj", type="secondary"):
            clear_auth_data()
            st.rerun()
    
    # Pobieranie i wyświetlanie danych
    with st.spinner("Pobieranie danych..."):
        try:
            orderlist = get_all_orders(auth_data['access_token'], auth_data['base_url'])
            
            # Liczenie zamówień o statusach 22 i 28
            status_counts = Counter(
                o["status"] for o in orderlist.get("orders", [])
                if o.get("status") in [22, 28]
            )
            total_orders = sum(status_counts.values())
            
            # Wyświetlanie głównej liczby
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown(f"""
                <div style="text-align: center;">
                    <h2>Nowe zamówienia:</h2>
                    <h1 style="font-size: 120px; margin: 0; color: #1f77b4;">{total_orders}</h1>
                </div>
                """, unsafe_allow_html=True)
            
            # Dodatkowe informacje
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Status 22 (Wiadomości)", status_counts.get(22, 0))
            with col2:
                st.metric("Status 28 (List przewozowy)", status_counts.get(28, 0))
            
            # Informacja o ostatnim odświeżeniu - poprawiony czas na polską strefę
            poland_tz = pytz.timezone('Europe/Warsaw')
            current_time = datetime.now(poland_tz)
            st.caption(f"Ostatnie odświeżenie: {current_time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            st.error(f"❌ Błąd podczas pobierania danych: {str(e)}")
            if st.button("Sprawdź połączenie"):
                if not connection_test(auth_data['access_token'], auth_data['base_url']):
                    st.error("Token wygasł lub jest nieprawidłowy. Zaloguj się ponownie.")
                    clear_auth_data()
                    st.rerun()

# -------------------------------
# Główna logika aplikacji
# -------------------------------

def main():
    # Sprawdzenie czy użytkownik jest zalogowany
    auth_data = get_auth_data()
    
    if auth_data is None:
        show_auth_form()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
