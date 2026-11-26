"""
ca_es_terms.py — Equivalències de cerca català → castellà de partida (Pla 050, ampliades al 097).

Pla 098: la font de veritat és la taula `search_terms`, editable des del panell d'administració.
Aquest diccionari només serveix per sembrar-la la primera vegada (migració 017, db.py) i com a
reserva si la base de dades no respon. Claus i valors en forma normalitzada (minúscules, sense
accents).
"""

SEED_TERMS: dict[str, str] = {
    # Alimentació i hoteleria
    'cuina': 'cocina', 'cuiner': 'cocinero', 'cuinera': 'cocinera',
    'pastisseria': 'pasteleria', 'hostaleria': 'hosteleria',
    'turisme': 'turismo',
    # Artesania i fusta
    'fusteria': 'carpinteria', 'fuster': 'carpintero',
    'cuir': 'cuero', 'vidre': 'vidrio',
    # Bellesa i imatge personal
    'perruqueria': 'peluqueria', 'bellesa': 'belleza',
    # Construcció i instal·lacions
    'paleta': 'albanil',
    # Comerç i màrqueting
    'comerc': 'comercio',  # comerç normalitzat: comerc (ç→c)
    'vendes': 'ventas', 'venda': 'venta',
    'publicitat': 'publicidad',
    # Educació i serveis socials
    'infermeria': 'enfermeria', 'infermer': 'enfermero', 'infermera': 'enfermera',
    # Esport i activitats físiques
    'esport': 'deporte', 'esports': 'deportes',
    # Finances i assegurances
    'assegurances': 'seguros', 'asseguranca': 'seguro',  # ç→c
    'inmobiliaria': 'inmobiliaria',  # immobiliària→inmobiliaria (doble m→m)
    # Imatge i so
    'imatge': 'imagen',
    # Seguretat i emergències
    'bombers': 'bomberos',
    # Arts i espectacle
    'dansa': 'danza', 'teatre': 'teatro', 'cinema': 'cine',
    'arts': 'artes', 'art': 'arte',
    'grafic': 'grafico',  # gràfic→grafic
    # Transport
    'transport': 'transporte',
    # Muntatge i instal·lació
    'muntatge': 'montaje', 'muntador': 'montador',
    # Pla 097: paraules freqüents dels títols de les especialitats del SEPE (només les que la
    # forma catalana no ja troba sola, com a part de la castellana o amb les regles de sufix)
    'operacions': 'operaciones', 'disseny': 'diseno', 'dissenyador': 'disenador', 'tecniques': 'tecnicas',
    'desenvolupament': 'desarrollo', 'nivell': 'nivel', 'sistemes': 'sistemas',
    'instal·lacions': 'instalaciones', 'instal·lacio': 'instalacion', 'instalacions': 'instalaciones',
    'instal·lador': 'instalador', 'aplicacions': 'aplicaciones', 'productes': 'productos',
    'producte': 'producto', 'dades': 'datos', 'avancat': 'avanzado', 'avancada': 'avanzada',
    'avancats': 'avanzados', 'avancades': 'avanzadas', 'persones': 'personas', 'projectes': 'proyectos',
    'projecte': 'proyecto', 'fonaments': 'fundamentos', 'fonament': 'fundamento', 'riscos': 'riesgos',
    'risc': 'riesgo', 'eines': 'herramientas', 'eina': 'herramienta', 'basiques': 'basicas',
    'treballs': 'trabajos', 'treball': 'trabajo', 'treballador': 'trabajador', 'treballadors': 'trabajadores',
    'digitals': 'digitales', 'auxiliars': 'auxiliares', 'activitats': 'actividades', 'serveis': 'servicios',
    'servei': 'servicio', 'xarxes': 'redes', 'xarxa': 'redes', 'processos': 'procesos',
    'laborals': 'laborales', 'equips': 'equipos', 'socials': 'sociales', 'qualitat': 'calidad',
    'intel·ligencia': 'inteligencia', 'intelligencia': 'inteligencia', 'professional': 'profesional',
    'professionals': 'profesionales', 'professio': 'profesion', 'vehicles': 'vehiculos', 'vehicle': 'vehiculo',
    'tecnologies': 'tecnologias', 'mercaderies': 'mercancias', 'mercaderia': 'mercancia', 'neteja': 'limpieza',
    'empreses': 'empresas', 'maneig': 'manejo', 'competencies': 'competencias', 'cures': 'cuidados',
    'materials': 'materiales', 'centres': 'centros', 'centre': 'centro', 'programari': 'software',
    'conductors': 'conductores', 'organitzacio': 'organizacion', 'salut': 'salud', 'entorns': 'entornos',
    'angles': 'ingles', 'mobils': 'moviles', 'mobil': 'movil', 'tractament': 'tratamiento',
    'estrategies': 'estrategias', 'edificis': 'edificios', 'industrials': 'industriales',
    'procediments': 'procedimientos', 'llengua': 'lengua', 'llengues': 'lenguas', 'viatgers': 'viajeros',
    'calcat': 'calzado', 'drons': 'drones', 'modelatge': 'modelado', 'aprenentatge': 'aprendizaje',
    'actualitzacio': 'actualizacion', 'especials': 'especiales', 'residus': 'residuos',
    'automatitzacio': 'automatizacion', 'maquines': 'maquinas', 'aigua': 'agua', 'aigues': 'aguas',
    'estructures': 'estructuras', 'mitjancant': 'mediante', 'elevadores': 'elevadoras', 'noves': 'nuevas',
    'sensibilitzacio': 'sensibilizacion', 'avaluacio': 'evaluacion', 'electriques': 'electricas',
    'electrics': 'electricos', 'continguts': 'contenidos', 'fusta': 'madera', 'carrega': 'carga',
    'especialitzacio': 'especializacion', 'situacions': 'situaciones', 'mitjans': 'medios',
    'dispositius': 'dispositivos', 'estacions': 'estaciones', 'digitalitzacio': 'digitalizacion',
    'millora': 'mejora', 'models': 'modelos', 'comercialitzacio': 'comercializacion', 'impressio': 'impresion',
    'materies': 'materias', 'cooperatives': 'cooperativas', 'ordinador': 'ordenador',
    'ordinadors': 'ordenadores', 'aplicades': 'aplicadas', 'aplicat': 'aplicado', 'aplicats': 'aplicados',
    'virtuals': 'virtuales', 'assessorament': 'asesoramiento', 'incendis': 'incendios',
    'climatitzacio': 'climatizacion', 'ensenyament': 'ensenanza', 'optimitzacio': 'optimizacion',
    'esdeveniments': 'eventos', 'carretons': 'carretillas', 'carreto': 'carretilla', 'aliments': 'alimentos',
    'plataformes': 'plataformas', 'derivats': 'derivados', 'operaris': 'operarios',
    'infraestructures': 'infraestructuras', 'personals': 'personales', 'videojocs': 'videojuegos',
    'tall': 'corte', 'audiovisuals': 'audiovisuales', 'perilloses': 'peligrosas', 'perillosos': 'peligrosos',
    'financer': 'financiero', 'financera': 'financiera', 'pagines': 'paginas', 'certificat': 'certificado',
    'benestar': 'bienestar', 'plantes': 'plantas', 'solucions': 'soluciones', 'joieria': 'joyeria',
    'comercials': 'comerciales', 'comptabilitat': 'contabilidad', 'entitats': 'entidades',
    'enginyeria': 'ingenieria', 'clients': 'clientes', 'suport': 'apoyo', 'comunitats': 'comunidades',
    'auxilis': 'auxilios', 'primers': 'primeros', 'formigo': 'hormigon', 'lampisteria': 'fontaneria',
    'lampista': 'fontanero', 'cambrer': 'camarero', 'cambrera': 'camarera', 'magatzem': 'almacen',
    'emmagatzematge': 'almacenaje', 'dependent': 'dependiente', 'caixer': 'cajero',
    'carnisseria': 'carniceria', 'peixateria': 'pescaderia', 'forn': 'horno', 'fleca': 'panaderia',
    'ramaderia': 'ganaderia', 'muntanya': 'montana', 'xapa': 'chapa', 'guix': 'yeso', 'ferro': 'hierro',
    'metall': 'metal', 'metal·lic': 'metalico', 'metallic': 'metalico', 'alemany': 'aleman',
    'seguretat': 'seguridad', 'ciberseguretat': 'ciberseguridad', 'igualtat': 'igualdad',
    'habilitats': 'habilidades',
}
