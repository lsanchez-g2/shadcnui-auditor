# shadcn/ui Figma Audit Swarm — qué es y cómo funciona

## En una frase

Pegas una URL de Figma y recibes una auditoría de nivel senior de cuánto se parece ese design system (o un componente) a shadcn/ui: tokens, modos claro/oscuro, contraste, estados, variantes, layout y nombrado, en un reporte HTML interactivo con puntuación, lista de fixes priorizada y evidencia para cada hallazgo.

## Por qué existe

- El handoff diseño→desarrollo se rompe cuando Figma y el código de shadcn discrepan sin que nadie lo note: un botón de 44 px donde el código dice 32, un focus ring atado a un gris que no es `ring`, un token `secondary-foreground` que existe pero nada lo usa, un dark mode simulado en el nombre de la variable.
- Encontrar eso a mano en 130 component sets tarda días y depende de quién mire.
- El skill lo hace en ~15 minutos por componente, igual cada vez, contra la spec viva y no contra lo que alguien recuerda de ella.

## Cómo funciona

Un orquestador, ocho especialistas (cada uno con una sola responsabilidad), un revisor senior y dos scripts.

**Paso 1 — Extraer una sola vez**
- El orquestador identifica qué es la URL: archivo completo, página, component set o componente suelto.
- Descarga la documentación de shadcn de hoy y el código fuente real del componente desde el registry de shadcn.
- Extrae los datos de Figma vía el conector MCP: variables con valores Light/Dark y cadenas de alias, estilos, propiedades de componente y una muestra de variantes con padding, alturas, tipografía y tokens vinculados medidos.
- Todo se guarda en un snapshot en disco. Nada más vuelve a tocar Figma ni la web: los ocho especialistas razonan sobre datos idénticos.

**Paso 2 — Ocho especialistas en paralelo**
- **Tokens**: ¿el set semántico está completo y emparejado (superficie + foreground)? ¿el radius deriva de una sola base? ¿cada token cumple su rol documentado?
- **Variables**: niveles primitivo → semántico → componente; valores crudos donde debería haber alias; huérfanas; alias rotos; scopes incorrectos.
- **Modos**: ¿cada token tiene un valor deliberado en Light y en Dark?
- **Contraste**: ratios WCAG 2.1 de cada par superficie/foreground, calculados por script (con composición de alpha y soporte oklch), nunca estimados.
- **Estados**: matriz variante × estado, una sola convención de estados por librería, focus rings que realmente usen `ring`.
- **Componentes**: paridad 1:1 con la API de shadcn — nombres, variantes, tamaños, px medidos vs. clases Tailwind, anatomía, props.
- **Estilos**: estilos de texto y efectos vs. clases Tailwind; estilos que duplican variables.
- **Gobernanza**: descripciones, enlaces a docs, capas ocultas, drift de nombrado entre componentes hermanos, preparación para Code Connect.
- Todos escriben hallazgos en un mismo formato. Un hallazgo sin evidencia del snapshot y sin cita a la documentación de shadcn se rechaza.

**Paso 3 — Consolidar con código, no con opinión**
- Un script valida cada archivo de hallazgos, fusiona duplicados (ocho agentes describiendo el mismo focus ring en ocho frases pasan a ser un hallazgo acreditado a los ocho), marca desacuerdos y calcula la puntuación.
- Auditoría de componente → porcentaje de cumplimiento.
- Auditoría de sistema → health score ponderado: pairing 20 %, contraste 25 %, paridad de modos 20 %, arquitectura 20 %, cobertura de estados/variantes 15 %.
- Como el número sale de código, dos ejecuciones sobre el mismo archivo dan el mismo número.

**Paso 4 — Revisión senior**
- Un revisor lee los hallazgos consolidados, resuelve los desacuerdos, escribe el veredicto y el orden de fixes agrupado por causa raíz (un token faltante → seis capas sin vincular → un solo fix).
- Separa defectos reales de decisiones de marca deliberadas que simplemente difieren de shadcn.
- Puede bajar la severidad de un hallazgo con razón explícita. No puede añadir hallazgos ni subir severidades: la evidencia del especialista siempre pesa más que el juicio del revisor.

**Paso 5 — El reporte**
- Página HTML autocontenida: veredicto y puntuación, top de issues, orden de fixes con esfuerzo estimado.
- Cada hallazgo con valor actual / valor esperado / fix exacto / evidencia / enlace a la doc.
- Matriz de contraste con la matemática visible, matrices de cobertura.
- Lo que ya cumple (para que nadie "arregle" lo que no está roto).
- Inventario off-spec: lo que shadcn no define en absoluto.

## Reglas que no rompe

- Nunca audita de memoria: la spec se descarga en cada ejecución porque los defaults de shadcn han cambiado de forma material (escala de radius, tamaños de Button, Base UI como flavor por defecto).
- Nunca adivina un valor que podría leer; lo que no puede verificar se marca como no verificado en lugar de puntuarse.
- No inventa, no elimina, no añade: lo que está fuera de la spec de shadcn se lista como off-spec, nunca se mete en la puntuación.
- Cada fix está escrito para la persona que lo va a ejecutar: nombre exacto de variable, valor exacto, capa exacta.

## Veredictos

- **READY FOR HANDOFF** — sin hallazgos críticos ni altos, cumplimiento ≥ 90 %.
- **NEEDS FIXES** — el caso normal; se trabaja el orden de fixes.
- **BLOCKED (off-spec)** — la API del componente tiene variantes o propiedades que shadcn no define y nadie las ha documentado como intencionales. El reporte indica el desbloqueo más barato, normalmente una línea en la descripción del componente.

## Dónde se ha ejecutado hasta ahora

- Un design system en producción (un cliente, siete ejecuciones): Button, Card, Switch, Checkbox, Input, Dialog (modo componente, 75–84 % de cumplimiento) y el archivo completo (modo sistema, health 76/100 sobre 130 component sets, 1.999 checks).
- Hallazgos recurrentes en toda la librería: focus rings atados a un gris neutro en lugar de `ring`; todos los componentes un paso de tamaño Tailwind por encima de base-nova; `primary` que no cambia entre Light y Dark; 26 variables `custom/*` nombradas como strings de clases Tailwind y con hex crudos.

## Qué necesita para ejecutarse

- Una URL de Figma (archivo, página o componente).
- El conector MCP de Figma activo.
- Qué flavor de shadcn usa ingeniería: Base UI, Radix o React Aria (las APIs difieren).
- Lee la estructura de variables por sí mismo; si el archivo es de solo lectura, pide capturas del panel de Variables.

## Límites conocidos

- Los component sets grandes se muestrean (cada valor de cada eje en defaults más la fila completa de estados), no se inspeccionan variante a variante; las variantes no muestreadas quedan marcadas como tales.
- El estado de publicación no lo expone el conector de Figma.
- Un component set anidado dentro del auditado necesita su propia URL.
- El criterio del revisor sobre "decisión de marca vs. defecto" es un criterio: el reporte muestra su razonamiento para que puedas revertirlo.
