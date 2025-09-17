// static/utils.js

// URL base para todas las llamadas a la API. Solo se cambia en un lugar.
const API_URL = `${window.location.origin}/api`;

/**
 * Muestra una notificación temporal en la pantalla.
 * @param {string} mensaje - El mensaje a mostrar.
 * @param {string} [tipo='success'] - 'success' o 'error'.
 */
function mostrarNotificacion(mensaje, tipo = 'success') {
    const notification = document.createElement('div');
    notification.textContent = mensaje;
    const backgroundColor = tipo === 'error' ? '#dc3545' : '#28a745';
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; background: ${backgroundColor}; color: white;
        padding: 12px 20px; border-radius: 5px; z-index: 1001; font-size: 14px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2); animation: slideIn 0.3s ease;
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } } @keyframes slideOut { to { transform: translateX(110%); } }`;
    document.head.appendChild(styleSheet);
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Copia un texto al portapapeles.
 */
function copiarTexto(texto) {
    navigator.clipboard.writeText(texto).then(() => {
        mostrarNotificacion('Texto copiado al portapapeles');
    }).catch(err => {
        console.error('Error al copiar: ', err);
        mostrarNotificacion('Error al copiar', 'error');
    });
}

/**
 * Solicita al servidor abrir la carpeta de un caso.
 */
async function abrirCarpeta(sesionId) {
    try {
        const response = await fetch(`${API_URL}/abrir_carpeta/${sesionId}`);
        const data = await response.json();
        mostrarNotificacion(data.message || (data.success ? 'Comando enviado' : 'Error'), data.success ? 'success' : 'error');
    } catch (error) {
        console.error('Error al solicitar abrir carpeta:', error);
        mostrarNotificacion('Error de conexión al abrir carpeta', 'error');
    }
}

function finalizarCaso(sesionId) {
    if (!sesionId) {
        alert('No se pudo obtener el ID de sesión para finalizar el caso.');
        return;
    }
    if (confirm('¿Está seguro que desea finalizar este caso? Una vez finalizado, no aparecerá en la lista de casos activos.')) {
        fetch(`${API_URL}/completar_caso/${sesionId}`, { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    mostrarNotificacion('Caso finalizado correctamente.', 'success');
                    // Esperamos un poco para que el usuario vea la notificación antes de redirigir
                    setTimeout(() => window.location.href = '/', 1500);
                } else {
                    throw new Error('Error en el servidor al finalizar el caso.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mostrarNotificacion('Error al finalizar el caso.', 'error');
            });
    }
}