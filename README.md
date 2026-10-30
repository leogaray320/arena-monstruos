# Arena de Monstruos

Proyecto en Django con MySQL para administrar entrenadores y monstruos, simular combates y consultar rankings.

## Estado

Se alcanzaron los niveles **Bronce, Plata, Oro y Diamante**: CRUD de monstruos, listado filtrable y paginado, presupuesto de estadísticas, entrenadores registrables y listables, combates con historial, rankings ORM/SQL, objetos equipables, entrenamiento, fotos JPG/PNG (máximo 2 MB) y API JSON. Las fotos se guardan en `media/`, carpeta excluida del control de versiones.

No quedan funciones obligatorias de esos niveles pendientes. Como mejoras, se pueden mejorar el css, ect.
## Cómo levantar el proyecto (Windows / PowerShell)

1. Instala y ejecuta MySQL Server. En MySQL Workbench, crea la base:

   ```sql
   CREATE DATABASE arena_monstruos
     CHARACTER SET utf8mb4
     COLLATE utf8mb4_unicode_ci;
   ```

2. Desde esta carpeta, crea y activa un entorno virtual e instala dependencias:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Configura la conexión MySQL en la sesión de PowerShell (ajusta usuario y contraseña; no guardes contraseñas en el código):

   ```powershell
   $env:DB_NAME = "arena_monstruos"
   $env:DB_USER = "root"
   $env:DB_PASSWORD = "tu_contraseña_mysql"
   $env:DB_HOST = "127.0.0.1"
   $env:DB_PORT = "3306"
   ```

4. Crea las tablas y ejecuta el servidor:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

   Abre <http://127.0.0.1:8000/>. Para crear acceso al panel administrativo, ejecuta `python manage.py createsuperuser` y sigue las instrucciones; el panel está en <http://127.0.0.1:8000/admin/>.

Las variables de entorno deben configurarse en cada nueva sesión de PowerShell. Para pruebas automatizadas se puede usar el respaldo SQLite con `$env:DB_MOTOR = "sqlite"` antes de ejecutar `python manage.py test juego`.
