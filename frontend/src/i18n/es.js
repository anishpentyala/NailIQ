// Spanish translations. Keys mirror en.js; any missing key falls back to English.
export default {
  crop: {
    clubbing: "Forma de la uña (acropaquia)",
    koilonychia: "Forma de la uña (cuchara)",
    appearanceNote: "Este resultado describe el aspecto de la uña en la foto superior. No se midió el ángulo ni la profundidad del perfil lateral.",
  "title": "Selecciona la uña",
  "instructions": "Mueve y ajusta el recuadro alrededor de una uña. Incluye sus bordes y un poco de piel.",
  "photo": "Foto de la uña",
  "move": "Mover recuadro",
  "nw": "Ajustar esquina superior izquierda",
  "ne": "Ajustar esquina superior derecha",
  "sw": "Ajustar esquina inferior izquierda",
  "se": "Ajustar esquina inferior derecha",
  "confirm": "Usar esta uña",
  "retake": "Repetir foto",
  "appearance": "Aspecto en la foto"
},
  langName: 'Español',

  app: {
    tagline: 'Un revisor preventivo de la salud de las uñas',
    disclaimer:
      'Esta es una herramienta educativa de detección, no un diagnóstico. Solo indica si los signos de tus uñas son típicos o si vale la pena que un médico los revise.',
    serverError: 'No se pudo conectar con el servidor de análisis. ¿Está funcionando el backend?',
    settingsLabel: 'Configuración de accesibilidad e idioma',
  },

  nav: {
    label: 'Navegación principal',
    home: 'Inicio',
    scan: 'Escanear',
    history: 'Historial',
    learn: 'Aprender',
  },

  home: {
    title: 'Inicio',
    heroAlt: 'Ilustración de un teléfono escaneando una uña',
    heroTitle: 'Detecta cambios en tus uñas que merecen una revisión médica',
    heroText:
      'Algunos signos de anemia y de condiciones del corazón, los pulmones y el hígado aparecen primero en las uñas, pero cambian tan lento que es difícil notarlo por tu cuenta. Dos fotos rápidas revisan ocho de ellos.',
    cta: 'Iniciar un escaneo',
    whyTitle: 'Por qué importa',
    whyRows: {
      anemia: {
        name: 'Anemia',
        text: 'Afecta a unos 2 mil millones de personas en el mundo - las uñas pálidas o en forma de cuchara están entre sus primeros signos visibles.',
      },
      organs: {
        name: 'Condiciones del corazón, pulmones e hígado',
        text: 'La acropaquia y los cambios de color en las uñas pueden aparecer meses antes de que estas condiciones se diagnostiquen.',
      },
      baseline: {
        name: 'Demasiado lento para notarlo',
        text: 'Estos signos se desarrollan durante meses, así que casi nadie los detecta en el espejo. Una foto de referencia hace visible la tendencia.',
      },
    },
    whoFor:
      'Creado como una primera revisión gratuita para quienes no tienen chequeos médicos regulares - nunca un reemplazo de ellos.',
    latestAssessment: 'Última evaluación',
    confidencePct: '{pct}% de confianza',
    greeting: 'Hola',
    howNails: '¿Cómo están tus uñas hoy?',
    notScanned: 'Aún sin escanear',
    lastScan: 'Último escaneo {when}',
    noScans: 'Aún no hay escaneos',
    firstResult: 'Tu primer resultado aparecerá aquí.',
    scanId: 'ID del escaneo',
    howItWorks: 'Cómo funciona',
    steps: {
      side: { title: 'Perfil lateral', text: 'El dedo de lado, con la uña hacia la cámara.' },
      top: { title: 'Desde arriba', text: 'Mira directamente hacia abajo a la superficie de la uña.' },
      read: { title: 'Recibe tu lectura', text: 'Un resultado claro y no diagnóstico por cada signo.' },
    },
    screensFor: 'Qué revisa NailIQ',
    rows: {
      clubbing: { name: 'Acropaquia (dedos en palillo)', text: 'El ángulo donde la uña se une con la piel.' },
      koilonychia: { name: 'Coiloniquia', text: 'Curvatura en forma de cuchara de la lámina ungueal.' },
      leukonychia: { name: 'Leuconiquia', text: 'Manchas blancas o decoloración en la uña.' },
      melanonychia: { name: 'Melanoniquia', text: 'Una banda oscura a lo largo de la uña.' },
      pallor: { name: 'Palidez', text: 'Un tono de lecho ungueal pálido y sin color.' },
      cyanosis: { name: 'Cianosis', text: 'Un tinte azulado o amoratado en el lecho ungueal.' },
      terrys_nails: { name: 'Uñas de Terry', text: 'Uña mayormente blanca con una banda oscura en la punta.' },
      lindsays_nails: { name: 'Uñas de Lindsay', text: 'Uña dividida en mitad blanca y mitad rosada.' },
      onycholysis: { name: 'Onicólisis', text: 'La uña se separa del lecho ungueal en la punta.' },
      beaus_lines: { name: 'Líneas de Beau', text: 'Surcos que cruzan la superficie de la uña.' },
      muehrckes_lines: { name: 'Líneas de Muehrcke', text: 'Bandas pálidas que cruzan el lecho ungueal.' },
      splinter_hemorrhages: { name: 'Hemorragias en astilla', text: 'Pequeñas líneas oscuras bajo la uña.' },
      pitting: { name: 'Piqueteado', text: 'Pequeños hoyuelos en la superficie de la uña.' },
      onychogryphosis: {
        name: 'Onicogrifosis',
        text: 'Uña engrosada y crecida que se curva.',
      },
    },
    showAll: 'Ver los {n}',
    notYet: 'Otros seis signos aún se están validando y todavía no se informan.',
    showLess: 'Ver menos',
    dailyTip: 'Consejo del día',
    tips: [
      'Una buena iluminación y un fondo liso hacen tu escaneo mucho más preciso.',
      'Las uñas sanas suelen ser lisas, con una curva leve y uniforme y sin surcos profundos.',
      'Los cambios en las uñas se desarrollan lentamente: revisarlas de vez en cuando te ayuda a notar tendencias.',
      'Apoya el dedo contra un borde para que la foto de perfil salga estable y nítida.',
      'Quita el esmalte antes de escanear para que la superficie de la uña sea visible.',
      'Una sola uña con aspecto raro rara vez es preocupante por sí sola; los patrones en varias uñas importan más.',
      'Encuadra un solo dedo, llenando la mayor parte del cuadro, para la lectura más clara.',
    ],
  },

  camera: {
    steps: {
      side: {
        instructions:
          'Sostén tu dedo de lado (vista de perfil) dentro del recuadro guía, con la uña hacia la cámara. Usa un fondo liso que llene todo el encuadre.',
        shortLabel: 'Perfil lateral',
      },
      top: {
        instructions:
          'Ahora fotografía tu dedo desde arriba dentro del recuadro guía, con la uña hacia la cámara. Usa un fondo liso que llene todo el encuadre.',
        shortLabel: 'Desde arriba',
      },
    },
    close: 'Cerrar cámara',
    flash: 'Activar o desactivar flash',
    switchCam: 'Cambiar de cámara',
    capture: 'Tomar foto',
    dismiss: 'Descartar mensaje',
    checkFailed: 'No se pudo verificar esa foto. ¿Está funcionando el backend?',
    captureFailed: 'No se pudo capturar la imagen. Asegúrate de que la cámara esté permitida e inténtalo de nuevo.',
    cameraBlocked: 'El acceso a la cámara fue bloqueado o no está disponible. Revisa los permisos del navegador y recarga la página.',
    fileFailed: 'No se pudo leer ese archivo. Prueba con otra foto.',
    checking: 'Verificando la foto…',
    analyzing: 'Analizando…',
    upload: 'Subir una foto en su lugar',
    stepOf: 'Paso {n} de 2',
  },

  verdict: {
    within: {
      label: 'Dentro del rango típico',
      message:
        'Observa los cambios con el tiempo y consulta siempre con un médico cualquier preocupación de salud.',
    },
    outside: {
      label: 'Fuera del rango típico',
      message: 'Vale la pena mostrárselo a un médico. No es un diagnóstico.',
    },
    inconclusive: {
      label: 'No se pudo analizar esta foto',
    },
  },

  result: {
    scanResults: 'Resultados del escaneo',
    tapCard: 'Toca un signo para ver detalles',
    reportTitle: 'Informe de detección de salud de uñas NailIQ',
    summaryWithin: 'Todo parece estar dentro del rango típico.',
    summaryOutsideOne: '1 signo está fuera del rango típico.',
    summaryOutside: '{n} signos están fuera del rango típico.',
    summaryInconclusive: 'No pudimos analizar este escaneo. Intenta tomar las fotos de nuevo.',
    howSure: 'Qué tan seguros estamos',
    noSignsRead: 'No se pudo leer ningún signo',
    signsUnreadOne: '1 signo no se pudo leer',
    signsUnread: '{n} signos no se pudieron leer',
    inTheseReadings: 'en estas lecturas',
    worthFollowingUp: 'Merece seguimiento',
    notARiskScore: 'No es un diagnóstico ni una puntuación de riesgo.',
    low: 'Bajo',
    some: 'Medio',
    high: 'Alto',
    photoQuality: 'Calidad de las fotos',
    qualityGood: 'Buena',
    qualityFair: 'Regular',
    qualityPoor: 'Mala',
    bothClear: 'Ambas fotos salieron claras',
    sidePhoto: 'foto de perfil',
    topPhoto: 'foto desde arriba',
    issueBlurry: 'borrosa',
    issueGlare: 'reflejos',
    issuePolish: 'esmalte de uñas',
    nextSteps: 'Próximos pasos',
    nextStepsOutside:
      'Uno o más signos salieron fuera del rango típico. Esto no es un diagnóstico: vale la pena mostrárselo a un médico, sobre todo si has notado otros síntomas.',
    nextStepsFallback: 'Vale la pena mencionárselo a un médico.',
    nextStepsDoctor:
      'Un médico de cabecera o un dermatólogo es la persona indicada para verlo. Usa "Guardar / imprimir informe" abajo para llevar una copia - los valores medidos son más útiles que una descripción de memoria.',
    nextStepsInconclusiveOne:
      'No pudimos analizar un signo con estas fotos. Tomarlas de nuevo con luz más brillante y uniforme, con la uña llenando el cuadro, suele solucionarlo.',
    nextStepsInconclusive:
      'No pudimos analizar {n} signos con estas fotos. Tomarlas de nuevo con luz más brillante y uniforme, con la uña llenando el cuadro, suele solucionarlo.',
    nextStepsWithin:
      'Todo parece estar dentro del rango típico. No hay nada que hacer por ahora: observa los cambios con el tiempo y consulta con un médico cualquier preocupación de salud.',
    groupCloserLook: 'Merece una mirada más de cerca',
    diagramOverviewAlt: 'Ilustración que muestra dónde se encontró cada señal de este escaneo',
    diagramOverviewNote: 'Una ilustración simplificada de dónde aparecen estas señales - no a escala, no es una foto de tu uña.',
    diagramClubbing: 'Acropaquia',
    diagramKoilonychia: 'Coiloniquia',
    groupCouldntAnalyze: 'No se pudo analizar',
    withinCount: '{n} dentro del rango típico',
    closestMatch: 'Coincidencia visual más cercana: {label} · {pct}% de confianza',
    mlClosestMatch: 'Coincidencia visual más cercana del modelo de IA: {label}',
    savePrint: 'Guardar / imprimir informe',
    scanAgain: 'Escanear de nuevo',
    disclaimer:
      'NailIQ es una herramienta educativa de detección, no un dispositivo médico. No diagnostica ninguna condición. Consulta siempre a un médico sobre tus preocupaciones de salud.',
    sources:
      'Método y honestidad: el umbral del ángulo de acropaquia sigue a Hsu et al. (2024); las revisiones de color y textura usan umbrales heurísticos sin calibrar y son señales de detección, no mediciones. Las lecturas de color se ajustan a la iluminación y al tono de piel, pero su precisión en el mundo real no está verificada.',
    measuredCaption: 'El recuadro muestra el área de la uña que midieron las revisiones de color.',
    measuredToggle: 'Área medida',
    gradcamToggle: 'Atención de la IA',
    gradcamCaption: 'Los colores más cálidos muestran de dónde salió la predicción del modelo de IA.',
    gradcamAlt: 'Mapa de calor que muestra en qué parte de tu uña se basó la predicción del modelo de IA',
    photoAlt: 'Tu foto de la uña desde arriba',
    badgeMl: 'Modelo de IA',
    badgeFused: 'Geometría + IA',
    badgeColor: 'Revisión de color',
    badgeColorFused: 'Color + IA',
    badgeLimited: 'Validación limitada',
    limitedNote: 'Validación limitada: esta revisión detectó menos del 60 % de los casos reales en nuestras pruebas; tómala con precaución.',
    feedbackQ: '¿Esto coincide con lo que ves?',
    feedbackYes: 'Sí',
    feedbackNo: 'No',
    feedbackThanks: 'Gracias - eso nos ayuda a mejorar.',
    feedbackImpact: 'Tus respuestas ayudan a calibrar resultados futuros.',
    toneCaveat: {
      limited:
        'Este tono de piel está subrepresentado en nuestros datos de prueba, así que esta lectura de color está menos validada para ti - trátala como una señal más débil.',
      minimal:
        'Tenemos muy pocos datos de validación para tonos de piel más oscuros, así que esta lectura de color puede no ser fiable para ti. No le des demasiada importancia.',
    },
    agreement: {
      agree: 'La medición de forma y el modelo de IA coinciden en esto.',
      geometry_only: 'Basado en la medición de forma; el modelo de IA no fue concluyente aquí.',
    },
    colorAgreement: {
      agree: 'La revisión de color y el modelo de IA coinciden en esto.',
      color_only: 'Basado en la revisión de color; el modelo de IA no fue concluyente aquí.',
      ml_primary: 'Basado principalmente en el modelo de IA.',
      ml_only: 'Basado solo en el modelo de IA: no hay una revisión de color más simple para este signo.',
    },
    mlLabels: {
      clubbing: 'apariencia tipo acropaquia',
      koilonychia: 'apariencia tipo coiloniquia (cuchara)',
      healthy: 'una uña de aspecto típico y saludable',
      cyanosis: 'una apariencia azulada (tipo cianosis)',
      terrys_nails: 'una apariencia tipo uñas de Terry',
      beaus_lines: 'un surco tipo línea de Beau',
      muehrckes_lines: 'un bandeado tipo líneas de Muehrcke',
      pitting: 'una superficie con piqueteado',
      onychogryphosis: 'una uña engrosada y crecida (tipo onicogrifosis)',
      pallor: 'una apariencia pálida (tipo palidez)',
    },
  },

  history: {
    title: 'Historial',
    loading: 'Cargando tus escaneos anteriores…',
    error: 'No se pudo cargar tu historial de escaneos. ¿Está funcionando el backend?',
    empty: 'Aún no hay escaneos. Tus resultados anteriores aparecerán aquí para que puedas seguir los cambios con el tiempo.',
    rescanNote:
      'Las uñas crecen unos 3 mm al mes, así que estos signos cambian despacio. Un reescaneo mensual hace visible una tendencia mucho antes de que sea obvia en el espejo.',
    placeholderNote: 'Mostrando escaneos de ejemplo. Haz tu primer escaneo para reemplazarlos con resultados reales.',
    example: 'Ejemplo',
    changed: 'Cambió',
    changedSinceLast: 'Cambió desde el último escaneo',
    withinRange: 'Dentro del rango',
    outsideRange: 'Fuera del rango',
    inconclusive: 'No concluyente',
    measuredAngle: 'Ángulo medido',
    measuredValue: 'Valor medido',
    clubbingThreshold: 'umbral > 180°',
    confidenceScore: 'Puntuación de confianza',
    fusedNote: 'Resultado combinado de varios modelos de análisis para mayor precisión.',
    colorFusedNote: 'Resultado combinado de una revisión de color y un modelo de IA para mayor precisión.',
    trendTitle: 'Ángulo de acropaquia a lo largo del tiempo',
    trendAngle: 'Ángulo',
    trendNote:
      'Esto solo registra el ángulo medido, no un diagnóstico. Comparte esta tendencia con un médico si tienes dudas.',
  },

  info: {
    intro:
      'NailIQ revisa cada foto en busca de todos estos signos. Toca cualquiera para aprender cómo se ve, por qué ocurre y qué significa tu resultado.',
    close: 'Cerrar',
  },

  failure: {
    invalid_image: 'Esa foto no se pudo procesar. Inténtalo de nuevo.',
    camera_feed_blank:
      'No recibimos una imagen real de tu cámara. Comprueba que el acceso a la cámara esté permitido y vuelve a cargar la página.',
    too_blurry:
      'Esa foto se ve borrosa. Mantén la mano y la cámara firmes, deja que enfoque y vuelve a tomarla.',
    no_contour_found:
      'No pudimos encontrar tu dedo en esa foto. Asegúrate de que llene el cuadro contra un fondo liso.',
    contour_too_small: 'Tu dedo se ve muy pequeño en el cuadro. Acerca la cámara e inténtalo de nuevo.',
    contour_degenerate: 'Esa foto no se pudo procesar. Inténtalo de nuevo.',
    background_not_filling_frame:
      'Algo detrás de tu dedo se está leyendo como parte de él. Usa una superficie lisa que llene todo el encuadre y vuelve a tomar la foto.',
    fingertip_cropped:
      'La punta de tu dedo queda cortada en el borde del cuadro. Muévela para que quede totalmente visible y vuelve a tomar la foto.',
    fingertip_not_clear:
      'No pudimos ver con claridad la punta de tu dedo. Prueba con mejor iluminación y mantén la cámara firme.',
    cuticle_not_detected:
      'No pudimos encontrar tu uña y cutícula con claridad. Asegúrate de que toda la uña sea visible, mirando hacia la cámara.',
    points_too_close:
      'No pudimos obtener una lectura clara de la forma de tu uña. Reposiciona el dedo y vuelve a tomar la foto.',
    points_collinear:
      'No pudimos obtener una lectura clara de la forma de tu uña. Reposiciona el dedo y vuelve a tomar la foto.',
    measurement_unstable: 'No pudimos medir el perfil lateral de tu uña de forma consistente: pequeños cambios en la foto dieron resultados distintos, así que no damos un resultado. Vuelve a tomar la foto lateral con la mano quieta, buena luz y un fondo liso.',
    angle_implausible: 'El ángulo de la uña que medimos no es físicamente posible, así que probablemente el contorno se leyó mal. Vuelve a tomar la foto lateral con el dedo completamente de perfil.',
    measurement_borderline: 'El ángulo de tu uña quedó justo en el límite del rango típico, demasiado cerca para decidir con fiabilidad. Vuelve a tomar la foto lateral de perfil y sin moverte; si te preocupa, consulta a un médico.',
    not_validated:
      "Todavía no hemos demostrado que esta comprobación sea lo bastante fiable en fotos de prueba, así que no damos un resultado en lugar de arriesgarnos a uno incorrecto. Si te preocupa este signo, consulta a un médico.",
    heuristic_uncorroborated:
      "Solo la comprobación de color más simple lo detectó y el modelo de IA no vio indicios, así que no damos un resultado. Vuelve a tomar la foto desde arriba con luz uniforme; si te preocupa, consulta a un médico.",
    low_confidence:
      'El modelo de IA no tuvo suficiente confianza con esta foto para dar una lectura. Prueba con una toma más clara y bien iluminada de una sola uña.',
    nail_region_unclear:
      'No pudimos obtener una lectura clara de la lámina de tu uña en la foto desde arriba. Llena el cuadro con tu uña bajo luz uniforme y vuelve a tomarla.',
    nail_polish_detected:
      'Parece que hay esmalte en la uña. Los signos de color y superficie no se pueden leer a través del esmalte: quítalo y vuelve a tomar la foto desde arriba.',
    too_much_glare:
      'Hay demasiado reflejo en la uña para leer su color. Inclínala lejos de la luz directa o busca una luz más suave, y vuelve a tomar la foto.',
    tracks_disagree:
      'Nuestras dos revisiones no coincidieron en este signo, así que no lo llamamos en ningún sentido. Vuelve a tomar ambas fotos con buena luz, y considera mostrárselo a un médico si te preocupa.',
    insufficient_data_for_confident_call:
      'No tenemos suficientes datos validados sobre este signo para determinarlo con confianza, y nuestras dos revisiones no coincidieron. Vuelve a tomar la foto con buena luz, y considera mostrárselo a un médico si te preocupa.',
    requires_ai_model: 'Este signo solo lo puede revisar el modelo de IA, que no está disponible en este momento, así que no damos un resultado.',
    no_confident_ai_call: 'El modelo de IA no estuvo lo bastante seguro sobre este signo en tu foto para dar un resultado. Vuelve a tomar la foto desde arriba con buena luz y la uña completa a la vista; considera consultar a un médico si te preocupa.',
    default:
      'No pudimos detectar una uña en esa foto. Prueba con un fondo más liso, mejor iluminación y todo el dedo dentro del cuadro.',
  },

  status: {
    outsideCount: '{n} fuera del rango típico',
    allWithin: 'Todo dentro del rango típico',
    cantAnalyze: 'No se pudo analizar este escaneo',
  },

  time: {
    justNow: 'Ahora mismo',
    minutesAgo: 'hace {n} min',
    hoursAgo: 'hace {n} h',
    yesterday: 'Ayer',
    daysAgo: 'hace {n} días',
  },

  diagram: {
    typical: 'Típica',
    typicalSub: 'uniforme, lisa',
    sign: 'Signo',
    alt: 'Vista superior de una uña típica comparada con una que muestra {sub}',
    fallbackSub: 'un signo',
    imgAlts: {
      clubbing:
        'Comparación lado a lado de un dedo con acropaquia (punta abultada y agrandada, uña curvada hacia abajo, lecho ungueal más ancho) frente a un dedo normal (punta afilada, uña más plana, lecho más estrecho)',
      koilonychia:
        'Comparación lado a lado de uñas normales (planas o ligeramente abombadas, de sección convexa) frente a coiloniquia (uñas en forma de cuchara que se hunden cóncavas en el centro)',
      leukonychia:
        'Comparación lado a lado de uñas normales frente a leuconiquia (pequeñas manchas blancas puntiformes repartidas por la lámina de la uña)',
      melanonychia:
        'Comparación lado a lado de uñas normales frente a melanoniquia (una única banda longitudinal de color marrón oscuro a negro que recorre la lámina de la uña)',
      pallor:
        'Comparación lado a lado de un lecho ungueal rosado normal frente a palidez (un lecho ungueal pálido y desvaído)',
      cyanosis:
        'Comparación lado a lado de un lecho ungueal rosado normal frente a cianosis (un lecho ungueal azulado y apagado)',
      terrys_nails:
        'Comparación lado a lado de uñas normales frente a uñas de Terry (una lámina mayormente blanca y opaca con una banda oscura estrecha en la punta)',
      lindsays_nails:
        'Comparación lado a lado de uñas normales frente a uñas de Lindsay (mitad y mitad): una mitad proximal blanca apagada y una mitad distal rosada-marrón más oscura con una línea divisoria nítida',
      onycholysis:
        'Comparación lado a lado de uñas normales frente a onicólisis (la lámina de la uña se separa y levanta del lecho en el borde libre distal, dejando un área despegada blanca o blanco-amarillenta)',
      beaus_lines:
        'Comparación lado a lado de uñas normales frente a líneas de Beau (un surco o depresión transversal que cruza la lámina de la uña)',
      muehrckes_lines:
        'Comparación lado a lado de uñas normales frente a líneas de Muehrcke (un par de bandas blancas transversales que cruzan la lámina de la uña)',
      splinter_hemorrhages:
        'Comparación de uñas normales frente a hemorragias en astilla típicas (líneas verticales pequeñas, finas y de color marrón rojizo bajo la uña)',
      pitting:
        'Comparación lado a lado de uñas normales (superficie lisa) frente a piqueteado ungueal (numerosas depresiones pequeñas, definidas e irregulares repartidas por la lámina de la uña)',
    },
    subs: {
      leukonychia: 'manchas blancas',
      melanonychia: 'banda oscura',
      pallor: 'pálida',
      cyanosis: 'azulada',
      terrys_nails: 'blanca, punta oscura',
      lindsays_nails: 'mitad y mitad',
      onycholysis: 'punta levantada',
      beaus_lines: 'surco transversal',
      muehrckes_lines: 'bandas blancas',
      splinter_hemorrhages: 'líneas diminutas',
      pitting: 'hoyuelos pequeños',
      onychogryphosis: 'gruesa, curva',
    },
  },

  settings: {
    title: 'Configuración',
    open: 'Abrir configuración',
    close: 'Cerrar configuración',
    language: 'Idioma',
    display: 'Pantalla y movimiento',
    darkMode: 'Modo oscuro',
    darkModeDesc: 'Usa un tema de color oscuro. Sigue la configuración de tu dispositivo salvo que la cambies aquí.',
    highContrast: 'Alto contraste',
    highContrastDesc: 'Colores y contornos más fuertes para leer con más facilidad.',
    largeText: 'Texto más grande',
    largeTextDesc: 'Aumenta el tamaño del texto en toda la aplicación.',
    reduceMotion: 'Reducir movimiento',
    reduceMotionDesc: 'Desactiva las animaciones y transiciones.',
    note: 'Esta configuración se guarda en este dispositivo.',
    privacyLink: 'Política de privacidad',
  },

  privacy: {
    title: 'Política de privacidad',
    close: 'Cerrar política de privacidad',
    photosTitle: 'Tus fotos',
    photosBody:
      'Tus dos fotos se analizan en memoria y luego se descartan. Ninguna foto se guarda nunca en disco ni en la base de datos: solo se almacenan los resultados (etiquetas, veredictos, confianza).',
    storedTitle: 'Qué se almacena',
    storedBody:
      'Los resultados de los escaneos se guardan localmente para que el Historial y el gráfico de tendencia del ángulo puedan mostrar escaneos anteriores. Si respondes "¿esto coincide con lo que ves?", esa respuesta se almacena de la misma manera para ayudar a calibrar la aplicación más adelante; evita incluir información identificable en el campo de notas. La configuración de pantalla e idioma se guarda solo en este dispositivo.',
    notCollectedTitle: 'Qué no se recopila',
    notCollectedBody: 'No se solicita ni almacena ninguna cuenta, nombre, correo electrónico o identificador de dispositivo en ninguna parte de esta aplicación.',
    limitationTitle: 'Limitación conocida',
    limitationBody:
      'Este es un prototipo de implementación única: el Historial muestra todos los escaneos almacenados en este servidor, sin separación por usuario. Ten esto en cuenta si este servidor llega a compartirse más allá de una persona.',
    disclaimer:
      'Nada en esta aplicación es un diagnóstico. Cada resultado es siempre "dentro del rango típico", "fuera del rango típico" o "no se pudo analizar esta foto". Habla con un profesional de la salud sobre cualquier cambio preocupante en las uñas.',
  },

  findingNames: {
    clubbing: 'Ángulo de la uña (acropaquia)',
    koilonychia: 'Curvatura de la uña (coiloniquia)',
    leukonychia: 'Color de la uña (leuconiquia)',
    melanonychia: 'Pigmentación de la uña (melanoniquia)',
    pallor: 'Color de la uña (palidez)',
    cyanosis: 'Color de la uña (cianosis)',
    terrys_nails: 'Color de la uña (uñas de Terry)',
    lindsays_nails: 'Color de la uña (uñas mitad y mitad)',
    onycholysis: 'Separación de la uña (onicólisis)',
    beaus_lines: 'Superficie de la uña (líneas de Beau)',
    muehrckes_lines: 'Marcas en la uña (líneas de Muehrcke)',
    splinter_hemorrhages: 'Marcas en la uña (hemorragias en astilla)',
    pitting: 'Superficie de la uña (piqueteado)',
    onychogryphosis: 'Engrosamiento de la uña (onicogrifosis)',
  },

  pointTitles: {
    looks: 'Cómo se ve',
    why: 'Por qué ocurre',
    how: 'Cómo lo revisa NailIQ',
    action: 'Qué hacer con tu resultado',
  },

  conditions: {
    clubbing: {
      name: 'Acropaquia (dedos en palillo de tambor)',
      summary: 'Un cambio en el ángulo donde la uña se une con la piel.',
      lead:
        'Mira tu dedo de lado. La mayoría de los dedos tienen una pequeña muesca donde la uña se une con la piel. La acropaquia suaviza esa muesca poco a poco hasta que la punta del dedo se ve redondeada y la uña se curva sobre ella.',
      points: {
        looks:
          'Normalmente hay una pequeña hendidura donde la uña se une con la piel del dedo, como un pequeño valle. Con la acropaquia, esa hendidura se aplana o desaparece, la punta del dedo se ve más redonda e hinchada y, con el tiempo, la uña puede empezar a curvarse hacia abajo sobre la punta en lugar de quedar plana.',
        why:
          'Los médicos no saben del todo por qué ocurre, pero aparece con más frecuencia junto a problemas pulmonares crónicos, ciertas condiciones cardíacas o algunas enfermedades digestivas. Se desarrolla lentamente a lo largo de meses o años, así que no es algo que aparezca de la noche a la mañana.',
        how:
          'Medimos el ángulo donde tu uña se une con la piel a partir de la foto de perfil. Un ángulo típico se mantiene por debajo de unos 180°. La acropaquia empuja ese ángulo más allá, así que en realidad es geometría cuidadosa, no una suposición.',
        action:
          'Un resultado "fuera del rango típico" no significa que tengas una enfermedad específica; solo significa que vale la pena mostrárselo a un médico, sobre todo si también has notado cosas como falta de aire, una tos persistente o un cansancio inusual.',
      },
    },
    koilonychia: {
      name: 'Coiloniquia (uñas en cuchara)',
      summary: 'Uñas que se curvan hacia arriba como una cuchara en lugar de quedar planas.',
      lead:
        'Mira tu uña directamente desde arriba. Una uña típica es plana o ligeramente abombada. Una uña en cuchara se hunde hacia adentro en el centro, a veces lo suficiente como para que una gota de agua se quede en ella en lugar de resbalar.',
      points: {
        looks:
          'En lugar de quedar plana o curvarse suavemente hacia afuera, el centro de la uña se hunde hacia adentro, como una pequeña cuchara. En los casos más notorios, la uña es tan delgada y curvada que una gota de agua se quedaría en el hueco en lugar de resbalar.',
        why:
          'La causa más común es el hierro bajo en la sangre, también llamado anemia ferropénica. También puede aparecer con cambios de tiroides, algunas condiciones de la piel o mucha exposición a solventes y detergentes fuertes. En bebés y niños pequeños, unas uñas ligeramente acucharadas suelen ser totalmente normales y se corrigen solas al crecer.',
        how:
          'Medimos cuánto se curva el centro de tu uña respecto a una línea recta trazada entre la cutícula y la punta del dedo, y luego lo ajustamos según el largo de tu uña para que funcione bien con dedos de distintos tamaños.',
        action:
          'Un resultado "fuera del rango típico" vale la pena mencionárselo a un médico, sobre todo si también te sientes inusualmente cansado, te ves pálido o tienes uñas quebradizas: eso puede apuntar a una anemia, que es fácil de detectar con un análisis de sangre sencillo y fácil de tratar.',
      },
    },
    leukonychia: {
      name: 'Leuconiquia (marcas blancas)',
      summary: 'Manchas o parches blancos en la superficie de la uña.',
      lead:
        'Las manchas, líneas o parches blancos en la uña se llaman leuconiquia. A veces aparecen solo unas pocas manchas tras un golpe o una lesión menor. Otras veces, áreas más grandes de la uña se ven blanquecinas en lugar del color rosado y blanco habitual.',
      points: {
        looks:
          'Las marcas blancas pueden aparecer como pequeñas manchas redondas, líneas horizontales finas, parches nublados más grandes o, en algunos casos, la mayor parte del lecho ungueal se ve blanca u opaca en lugar del color rosado típico bajo la lámina de la uña.',
        why:
          'Las manchas blancas pequeñas suelen venir de traumatismos menores o golpes en la uña. Un blanqueamiento extendido del lecho ungueal puede relacionarse con enfermedades del hígado, de los riñones, problemas cardíacos, diabetes o problemas nutricionales, pero también puede ser totalmente inofensivo. Solo un médico puede notar la diferencia.',
        how:
          'Estimamos la lámina de la uña a partir de una foto desde arriba y buscamos áreas blancas u opacas en la uña, ajustando según tu tono de piel. Son señales de detección, no mediciones precisas: la iluminación y las diferencias entre cámaras de teléfono afectan el resultado.',
        action:
          'Si ves una coloración blanca extensa en tus uñas, sobre todo si aparece en varios dedos, vale la pena mencionárselo a un médico: puede examinarte adecuadamente y pedir pruebas si hace falta. Las manchas blancas pequeñas por golpes menores suelen desaparecer solas.',
      },
    },
    melanonychia: {
      name: 'Melanoniquia (banda oscura)',
      summary: 'Una banda marrón o negra que recorre la uña a lo largo.',
      lead:
        'Una banda longitudinal oscura, una franja que va de la cutícula a la punta, se llama melanoniquia. Es muy común, sobre todo en personas con tonos de piel más oscuros, y a menudo es completamente benigna. Pero una banda nueva o que está cambiando merece la revisión de un médico.',
      points: {
        looks:
          'Una franja marrón, negra o gris oscura recorre la uña a lo largo, desde la cutícula hasta la punta, a veces ocupando todo el ancho de la uña o solo una parte. La banda puede ser estrecha o bastante ancha.',
        why:
          'La causa más común es el pigmento de las células que forman la uña (melanocitos), algo especialmente común en personas de piel más oscura y casi siempre benigno. Las bandas también pueden venir de lunares, marcas de nacimiento, medicamentos (como algunos de quimioterapia) o, en casos raros, de un melanoma. Una banda nueva o cambiante merece la atención de un médico.',
        how:
          'Estimamos la lámina de la uña y buscamos pigmentación marrón oscura o negra a lo largo de la uña. NailIQ ajusta su sensibilidad según tu tono de piel para tener en cuenta la variación normal. Estas revisiones son señales de detección, no diagnósticas.',
        action:
          'Si una banda oscura lleva mucho tiempo igual y sin cambios, es muy probable que sea inofensiva. Si es nueva, se está ensanchando, está cambiando de color o forma, o no sabes cuánto tiempo llevas con ella, muéstrasela a un médico: puede examinarla y decidir si hacen falta más pruebas.',
      },
    },
    pallor: {
      name: 'Palidez (uñas pálidas)',
      summary: 'Un lecho ungueal inusualmente pálido o blanco.',
      lead:
        'La mayoría de las uñas tienen un lecho rosado con la punta blanca. Cuando el lecho de la uña se ve inusualmente pálido o blanco, a veces puede relacionarse con hierro bajo, anemia, enfermedad del hígado o problemas renales, aunque también puede ser una variación normal.',
      points: {
        looks:
          'El lecho ungueal (la parte bajo la lámina transparente de la uña) se ve pálido, blanquecino o casi sin color en lugar del rosado típico. La punta de la uña puede seguir siendo blanca, pero el centro y la base se ven menos rosados de lo habitual.',
        why:
          'Las uñas pálidas pueden relacionarse con un recuento bajo de glóbulos rojos (anemia), hierro bajo, enfermedad del hígado, enfermedad renal o menor flujo de sangre a los dedos. También pueden ser simplemente una variación normal del tono de piel. Un médico necesita examinarte y quizá pedir análisis de sangre para saber la causa.',
        how:
          'Analizamos el color del lecho ungueal a partir de una foto desde arriba y buscamos palidez o blanqueamiento, ajustando según tu tono de piel. Es solo una señal de detección: no mide recuentos sanguíneos ni niveles de oxígeno.',
        action:
          'Unas uñas pálidas de forma generalizada, sobre todo en varios dedos, valen la pena mencionárselas a un médico durante una consulta. Si además te sientes cansado, mareado o con falta de aire, menciona también esos síntomas: pueden ayudar a tu médico a decidir si hacen falta análisis de sangre.',
      },
    },
    cyanosis: {
      name: 'Cianosis (uñas azuladas)',
      summary: 'Un tinte azulado o morado en las uñas.',
      lead:
        'Cuando las uñas tienen un tinte azulado o morado en lugar del rosado y blanco habitual, se llama cianosis. Puede relacionarse con oxígeno bajo en la sangre, exposición al frío o problemas del corazón o los pulmones, pero también puede ser un artefacto de la cámara o un efecto de la luz.',
      points: {
        looks:
          'El lecho y la lámina de la uña tienen un tinte azulado, morado o grisáceo en lugar del rosado típico. La decoloración puede afectar toda la uña o notarse más en el lecho ungueal.',
        why:
          'La cianosis verdadera (un tinte azulado por oxígeno bajo en la sangre) puede darse con enfermedades pulmonares, cardíacas o por frío intenso. Las uñas también pueden verse azules o moradas por moretones, la edad, dedos fríos o ciertos medicamentos. Los hongos en las uñas a veces también causan un tinte azulado.',
        how:
          'Analizamos el color del lecho y la lámina de la uña a partir de una foto desde arriba y buscamos tonos azulados o morados. Ten en cuenta que la iluminación, el balance de blancos de la cámara y el esmalte pueden afectar esto: son señales de detección, no una medición de oxígeno.',
        action:
          'Si tus uñas se ven realmente azuladas y además notas falta de aire, dolor en el pecho, o tus labios o lengua se ven azules, busca atención médica de inmediato. Si las uñas solo se ven un poco azules en las fotos pero te sientes bien, puede ser un artefacto de la cámara: un médico puede examinar tus uñas en persona para aclararlo.',
      },
    },
    terrys_nails: {
      name: 'Uñas de Terry',
      summary: 'La mayor parte de la uña blanca u opaca con una banda oscura estrecha en la punta.',
      lead:
        'En las uñas de Terry, el lecho ungueal se ve mayormente blanco u opaco, dejando solo una banda estrecha de color marrón rojizo u oscura en la punta. Este patrón suele asociarse con enfermedad del hígado, insuficiencia cardíaca, enfermedad renal o diabetes.',
      points: {
        looks:
          'La mayor parte de la uña (aproximadamente de dos tercios a tres cuartos) se ve blanca, opaca o pálida. Solo la punta muestra una banda más oscura de color marrón rojizo, normalmente de 1 a 3 mm de ancho. A veces una línea pálida fina separa el área blanca de la banda oscura.',
        why:
          'Las uñas de Terry se ven con más frecuencia con enfermedad del hígado, enfermedad renal, insuficiencia cardíaca o diabetes. También pueden aparecer tras la quimioterapia o con la edad. La causa exacta no se entiende del todo, pero el lecho ungueal cambia de una forma que lo hace verse más blanco. Se considera un signo clínico que merece investigación.',
        how:
          'Estimamos la lámina de la uña y buscamos una transición marcada entre un lecho mayormente blanco y una banda distal más oscura. Es una señal de detección: un diagnóstico adecuado requiere el examen de un médico.',
        action:
          'Si tus uñas coinciden con este patrón, sobre todo en varios dedos, vale la pena mostrárselas a un médico. Puede revisar tu salud general y quizá pedir pruebas (análisis de sangre, función hepática, función renal, examen cardíaco) para entender qué está pasando.',
      },
    },
    lindsays_nails: {
      name: 'Uñas mitad y mitad (uñas de Lindsay)',
      summary: 'Mitad proximal blanca, mitad distal de color marrón rojizo.',
      lead:
        'En las uñas de Lindsay hay una línea marcada que cruza el centro de la uña: la mitad más cercana a la cutícula es blanca o pálida, y la mitad hacia la punta es de color marrón rojizo o rosado. Este patrón suele asociarse con enfermedad renal.',
      points: {
        looks:
          'Una línea horizontal divide la uña aproximadamente por la mitad: la mitad proximal (cerca de la cutícula) es blanca, opaca o pálida, y la mitad distal (hacia la punta) es rojiza, rosada o marrón. La línea divisoria suele ser nítida y bien definida.',
        why:
          'Las uñas de Lindsay se asocian clásicamente con la enfermedad y la insuficiencia renal, sobre todo en pacientes en diálisis. También pueden darse con otras enfermedades serias, como enfermedad del hígado o leucemia. La causa exacta se desconoce, pero el patrón se considera un signo clínico que merece investigación.',
        how:
          'Estimamos los límites de la uña y buscamos una banda horizontal clara que separe una mitad proximal blanca de una mitad distal más oscura. Es una señal de detección basada en color y posición.',
        action:
          'Si tus uñas muestran este patrón, sobre todo en varios dedos, coméntaselo a un médico. Si tienes antecedentes de problemas renales, diabetes o enfermedad del hígado, menciónalo también: tu médico puede pedir las pruebas y el seguimiento adecuados.',
      },
    },
    onycholysis: {
      name: 'Onicólisis (uña despegada)',
      summary: 'La uña se separa del lecho y se ve opaca en el borde libre.',
      lead:
        'La onicólisis ocurre cuando la uña empieza a separarse del lecho ungueal, comenzando por el borde libre y avanzando hacia la cutícula. La parte separada se ve opaca o blanca en lugar del color transparente que tendría si siguiera adherida.',
      points: {
        looks:
          'La uña se levanta del dedo empezando por la punta y puede extenderse hacia la cutícula. El área levantada se ve opaca, blanquecina o como tiza en lugar de transparente. Puede que veas aire o residuos bajo la uña en la zona levantada.',
        why:
          'La onicólisis puede ser causada por traumatismos en la uña, enfermedad de tiroides (sobre todo hipertiroidismo), psoriasis, infección por hongos, dermatitis de contacto o reacciones a medicamentos o productos para uñas. A veces nunca se encuentra la causa. Suele resolverse a medida que la uña se renueva, pero el tratamiento depende de la causa de fondo.',
        how:
          'Buscamos áreas donde la uña parece separarse o levantarse del dedo, que se ven como zonas opacas o blancas, sobre todo en o cerca del borde libre. Es solo una revisión visual de detección.',
        action:
          'Si notas que la uña se despega, mantén el área seca y limpia para prevenir infecciones, y evita la manicura agresiva o la exposición a químicos fuertes. Muéstrasela a un médico si se extiende rápido, duele o aparecen signos de infección. Tu médico puede hacer pruebas de tiroides, psoriasis u hongos si hace falta.',
      },
    },
    beaus_lines: {
      name: 'Líneas de Beau',
      summary: 'Surcos o hendiduras horizontales que cruzan la uña.',
      lead:
        'Las líneas de Beau son surcos o hendiduras que cruzan el ancho de la uña, de lado a lado. Marcan una pausa o desaceleración temporal del crecimiento de la uña, normalmente causada por una enfermedad, fiebre alta, cirugía o estrés severo.',
      points: {
        looks:
          'Uno o más surcos o crestas horizontales cruzan todo el ancho de la uña de un lado al otro. Los surcos pueden ser superficiales o bastante profundos, y pueden verse más en algunos dedos que en otros.',
        why:
          'Las líneas de Beau se forman cuando las células que producen la uña se detienen o se ralentizan, algo que ocurre tras un estrés físico o emocional significativo: fiebre alta, una enfermedad seria, cirugía, una infección severa o una lesión importante. Aparecen aproximadamente en la zona de la uña que estaba creciendo en el momento del estrés. A medida que la uña crece, la línea se desplaza hacia la punta y acaba desapareciendo.',
        how:
          'Analizamos la superficie de la uña en busca de hendiduras o surcos horizontales que crucen su ancho. Es una revisión visual de detección basada en la textura de la superficie.',
        action:
          'Si notas líneas de Beau, intenta recordar si tuviste una enfermedad significativa, fiebre alta, cirugía o mucho estrés unas 6 a 12 semanas antes: la cronología suele coincidir. Las líneas de Beau en sí son inofensivas y desaparecen a medida que la uña crece. Si tienes líneas recurrentes u otros cambios preocupantes en las uñas, menciónalos a un médico.',
      },
    },
    muehrckes_lines: {
      name: 'Líneas de Muehrcke',
      summary: 'Bandas blancas en pares que cruzan la uña y no se mueven al crecer.',
      lead:
        'Las líneas de Muehrcke son pares de bandas blancas que cruzan la uña horizontalmente. A diferencia de las líneas de Beau, se quedan en la misma posición respecto a la cutícula a medida que la uña crece: no se desplazan hacia la punta. Suelen relacionarse con proteína baja en la sangre o enfermedad renal.',
      points: {
        looks:
          'Dos bandas blancas cruzan la uña horizontalmente, normalmente en la región media o proximal. Las bandas están separadas por una línea fina del color normal de la uña. A diferencia de las líneas de Beau (surcos), las líneas de Muehrcke son planas (sin hendidura): son puramente un cambio de color.',
        why:
          'Las líneas de Muehrcke se asocian clásicamente con proteína baja en la sangre (hipoalbuminemia), que puede darse con enfermedad renal, enfermedad del hígado, desnutrición u otras enfermedades serias. También pueden aparecer temporalmente durante el embarazo o con ciertos cánceres. Las líneas reflejan un cambio en el propio lecho ungueal y se quedan en su lugar a medida que la uña crece (a diferencia de las líneas de Beau, que se mueven hacia la punta).',
        how:
          'Buscamos pares de bandas blancas horizontales en la uña que sean planas (sin surco) y se mantengan aproximadamente en la misma posición a lo ancho de la uña. Es una revisión visual de detección.',
        action:
          'Si notas este patrón, sobre todo en varias uñas, coméntaselo a un médico. Suele apuntar a un problema renal o hepático que merece investigación. Tu médico puede pedir análisis de sangre para revisar los niveles de proteínas y la función renal y hepática.',
      },
    },
    splinter_hemorrhages: {
      name: 'Hemorragias en astilla',
      summary: 'Pequeñas líneas oscuras bajo la uña, a lo largo.',
      lead:
        'Las hemorragias en astilla son pequeñas líneas de color rojo oscuro, marrón o negro que corren a lo largo bajo la uña. Parecen pequeñas astillas de madera. La mayoría se deben a traumatismos menores, pero ocasionalmente pueden relacionarse con infecciones u otras condiciones.',
      points: {
        looks:
          'Una o más líneas finas y oscuras (rojas, marrones o negras) corren a lo largo bajo la uña, desde el lecho hacia la punta. Parecen pequeñas astillas, normalmente de unos pocos milímetros. Se notan más en las porciones media o distal de la uña.',
        why:
          'La mayoría de las hemorragias en astilla vienen de golpes o traumatismos menores en el dedo que dañan pequeños vasos sanguíneos bajo la uña. Sanan solas a medida que la uña crece. Ocasionalmente pueden ser un signo de una infección en la sangre (endocarditis), sobre todo si aparecen en varias uñas sin ninguna lesión evidente, o junto a otros síntomas como fiebre, escalofríos o un soplo cardíaco nuevo.',
        how:
          'Buscamos líneas oscuras longitudinales bajo la uña que podrían indicar pequeñas hemorragias. Es una revisión visual de detección: algunas líneas oscuras podrían ser artefactos de suciedad o de la cámara del teléfono.',
        action:
          'Si ves una hemorragia en astilla y recuerdas haberte golpeado el dedo, probablemente desaparecerá sola. Si varias uñas desarrollan hemorragias en astilla sin ninguna lesión, o si además tienes fiebre o te sientes mal, menciónalo a un médico: puede evaluar si hacen falta más pruebas.',
      },
    },
    pitting: {
      name: 'Piqueteado de la uña',
      summary: 'Pequeños hoyuelos o puntitos en la superficie de la uña.',
      lead:
        'El piqueteado es la aparición de pequeños hoyuelos, hendiduras o puntitos repartidos por la superficie de la uña. Se ve con frecuencia en la psoriasis, pero también puede aparecer con alopecia, enfermedades del tejido conectivo o, a veces, por sí solo.',
      points: {
        looks:
          'La superficie de la uña tiene varias hendiduras pequeñas, redondas o irregulares, como pequeños hoyos repartidos por la uña. Los hoyuelos pueden ser superficiales o más profundos, y pueden afectar solo la superficie o extenderse parcialmente hacia dentro de la uña. Le dan a la uña un aspecto más áspero.',
        why:
          'El piqueteado se relaciona sobre todo con la psoriasis (una condición de la piel) y la alopecia areata (pérdida de cabello en parches). También puede darse con enfermedades del tejido conectivo, infecciones por hongos o, a veces, por sí solo sin otra causa. El piqueteado por psoriasis suele afectar varias uñas.',
        how:
          'Analizamos la superficie de la uña en busca de pequeñas hendiduras y patrones de piqueteado. Es una revisión visual de detección basada en la textura de la superficie, aunque la resolución de la cámara y la iluminación afectan lo visibles que son los hoyuelos finos.',
        action:
          'Si notas piqueteado en varias uñas, vale la pena mencionárselo a un médico, sobre todo si también tienes síntomas en la piel como placas o picazón, o pérdida de cabello. Tu médico puede examinarte y decidir si hacen falta pruebas o una evaluación adicional.',
      },
    },
    onychogryphosis: {
      name: 'Onicogrifosis (uña en cuerno de carnero)',
      summary: 'Uña engrosada y crecida que se curva.',
      lead: 'La onicogrifosis es una uña que se ha vuelto muy gruesa y crecida, y que a menudo se curva como un cuerno. Afecta con más frecuencia la uña del dedo gordo del pie, pero también puede aparecer en las uñas de las manos. Suele deberse a presión prolongada, lesiones o la edad, y a veces se relaciona con mala circulación.',
      points: {
        looks: 'La uña es mucho más gruesa de lo normal, a menudo amarilla o marrón, y puede tener crestas transversales. Al crecer puede curvarse hacia un lado o hacia abajo sobre la punta del dedo, a veces como un cuerno de carnero.',
        why: 'Suele deberse a presión o lesiones repetidas en la uña (los zapatos apretados son una causa común en los pies), la edad o la falta prolongada de corte de uñas. También puede relacionarse con mala circulación, diabetes, psoriasis o infección por hongos. A diferencia de la mayoría de los signos que revisa NailIQ, suele ser un problema local de la uña y no un signo de una afección de todo el cuerpo.',
        how: 'Esta revisión proviene solo del modelo de IA: aprendió cómo se ven las uñas engrosadas y crecidas a partir de fotos clínicas etiquetadas. No hay una medición de color aparte, así que si el modelo no está seguro, decimos que no pudimos analizarla en lugar de adivinar.',
        action: 'Vale la pena mostrar una uña gruesa y crecida a un médico o podólogo, sobre todo si duele, es difícil de cortar o si tienes diabetes o mala circulación. Pueden cortarla de forma segura y revisar si hay algo debajo.',
      },
    },
  },
}
