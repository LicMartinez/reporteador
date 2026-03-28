# Despliegue del frontend en Vercel (SwissTools Dashboard)

Este documento evita la confusión entre **código en GitHub** y **lo que ves en producción** en `swiss-tools-dashboard.vercel.app`.

---

## Flujo acordado: Vercel CLI (no “solo GitHub”)

En este proyecto **el despliegue a producción se hace con la Vercel CLI** desde tu máquina (o CI que ejecute los mismos comandos), **no** se asume que un `git push` a `main` deja automáticamente el sitio público actualizado.

| Acción | ¿Actualiza producción sola? |
|--------|-----------------------------|
| `git push` a GitHub | **No**, si tu proceso oficial es desplegar con CLI. |
| `npx vercel deploy --prod` (desde `frontend/`) | **Sí** (sube y publica el build actual). |

**Regla práctica:** después de mergear mejoras en `main`, si quieres verlas en **producción**, ejecuta el deploy con CLI (pasos abajo). No basta con “ya está en GitHub”.

---

## Por qué en el pasado se veía la versión vieja (RestBar, dashboard antiguo)

1. **Producción en Vercel = último deploy con estado *Ready* asignado al dominio.**  
   Si los despliegues nuevos fallan (*ERROR*) o no se llegó a ejecutar ninguno, el dominio **sigue sirviendo el último bueno**, aunque el código en GitHub sea más nuevo.

2. **Origen “`vercel deploy`” en el panel**  
   Cuando el deployment muestra fuente **CLI** (`vercel deploy`), encaja con un flujo manual. Los commits en Git **no sustituyen** ese deploy hasta que vuelvas a publicar con la CLI (o hasta que exista otro pipeline que despliegue con éxito).

3. **Monorepo**  
   El `package.json` del dashboard está en **`frontend/`**, no en la raíz del repo. Si en Vercel el contexto de build es la raíz sin configuración adecuada, el build en la nube puede fallar. Por eso existe **`vercel.json` en la raíz** del repositorio con `installCommand` / `buildCommand` / `outputDirectory` apuntando a `frontend/` (y/o **Root Directory = `frontend`** en el panel de Vercel). Sin eso, los builds automáticos pueden quedar en *ERROR* y producción no avanza.

4. **Caché del navegador**  
   Tras un deploy bueno, si algo sigue igual, prueba recarga forzada o ventana de incógnito.

---

## Cómo desplegar a producción con Vercel CLI

Desde la raíz del repo, entra al frontend:

```powershell
cd c:\desarrollo\reporteador\frontend
```

Primera vez o nuevo equipo:

```powershell
npx vercel login
npx vercel link
```

Traer ajustes y variables del proyecto (recomendado antes de build local serio):

```powershell
npx vercel pull --yes --environment=production
```

**Opción A — Deploy directo (build en la nube):**

```powershell
npx vercel deploy --prod --yes
```

**Opción B — Build local y subir artefacto (útil para depurar):**

```powershell
npx vercel build --prod --yes
npx vercel deploy --prebuilt --prod --yes
```

Comprueba en el panel de Vercel que el deployment de **Production** esté *Ready* y que el dominio apunte a ese deployment.

---

## Variables de entorno en Vercel

- **`VITE_API_URL`**: URL pública del backend (p. ej. Render), **sin** barra final.  
  Se inyecta en **build**; si la cambias, hace falta **volver a desplegar** el frontend.

---

## GitHub y Vercel (aclaración)

Puede haber un proyecto en Vercel **conectado al mismo repositorio** de GitHub. En ese caso, un `git push` **puede** disparar builds en Vercel automáticamente.

Eso **no sustituye** la decisión de equipo de usar **CLI como flujo oficial**: mientras el procedimiento documentado sea “publicar con `vercel deploy --prod`”, hay que seguirlo después de cada entrega que deba verse en `swiss-tools-dashboard.vercel.app`.

Además, si el build automático por Git **falla**, producción **no** cambia: seguirás viendo la última versión desplegada con éxito (a veces antigua). Revisa siempre el estado *Ready* / *Error* en **Deployments**.

---

## Resumen

1. **Producción se actualiza** cuando hay un deployment **exitoso** a producción (en la práctica, con **Vercel CLI** según este flujo).  
2. **`git push` no es, por sí solo, el paso de publicación** si el acuerdo es desplegar con CLI.  
3. **Monorepo:** mantener coherente `vercel.json` en raíz y/o **Root Directory = `frontend`**.  
4. Tras problemas, revisar en Vercel la lista de deployments: si los nuevos están en *Error*, el sitio público puede seguir en una versión vieja *Ready*.

Para el relato general del MVP (Render, Supabase, variables), sigue siendo válido **`DEPLOY_MVP.md`**.
