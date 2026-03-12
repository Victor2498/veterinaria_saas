# Documentación Técnica - Veterinaria SaaS

Esta documentación resume los hallazgos técnicos y las implementaciones del módulo base.

## 1. Arquitectura Central
- **Backend:** Desarrollado con **FastAPI**, lo que garantiza alta simultaneidad y soporte estricto de tipado a lo largo del ruteador de la API REST.
- **ORM / Persistencia:** Implementado mediante **SQLAlchemy** sobre una base de datos **PostgreSQL**. Las migraciones se administran programáticamente.
- **Caché y Mensajería:** Utiliza **Redis** de manera extensiva para cachear configuraciones pesadas (por ejemplo: URLs de webhooks o llaves de OpenAI) limitando los hits hacia la DB.

## 2. Autenticación y Seguridad
- **JWT (JSON Web Tokens):** Las sesiones, tanto de super-administradores como de organizaciones, se basan en JWT almacenado en cookies firmadas HttpOnly para máxima seguridad en el frontend.
- **Autorización por Niveles:** El sistema está protegido por Middlewares (`admin_required`, `superadmin_required`). Se ha verificado que solo los administradores pueden invocar acciones de suscripciones (`finance.py` y `superadmin.py`).
- **Resiliencia ante Inyecciones:** Todas las transacciones SQL críticas utilizan SQLAlchemy queries parametrizadas o mapeo con modelos definidos (`select()`). Aquellos scripts sin utilizar los drivers ORM puros han sido parchados en `init_db.py`.

## 3. Integración de Servicios (Servicios Capa 3)
- **Evolution API (WhatsApp):** Los webhooks envían datos JSON decodificados a `webhook_processor.py`. El flujo es no bloqueante (`BackgroundTasks`) y la extracción multimedia fue robustecida para evadir loops fatales por errores (`try/except/continue`).
- **OpenAI:** Generación dinámica de reportes clínicos y transcripción iterativa del chat.
- **ReportLab (Generación de PDF):** Sistema avanzado de renderización PDF modular, preparado para emitir "Tickets de Pago" y "Libretas Sanitarias" que varían entre la suscripción estandar y la premium.

## 4. Diagnóstico de Rendimiento (Evaluación Final)
- Se erradicaron más de 20 dependencias innecesarias de toda la capa `src/api` aliviando la carga del hilo principal de CPython.
- Las consultas `SQLAlchemy` a través de colecciones complejas (como historiales y pagos) se gestionan a través de `JOIN` para mitigar el problema frecuente N+1 de bases no normalizadas.
