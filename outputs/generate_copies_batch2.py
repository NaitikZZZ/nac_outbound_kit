import csv
import re
import os

# ─── Company lines: Sentence 1 = what they sell. Sentence 2 = rep pain. ──────
COMPANY_LINE1 = {
    "Aeries Software": "Aeries Software sells student information systems into K-12 districts. Your reps are navigating procurement with district administrators and IT directors, and each stakeholder conversation generates follow-up that is probably still done manually.",
    "Aerospike": "Aerospike sells a real-time data platform into enterprises. Your reps are running deep technical evaluations with engineering and infrastructure teams, plus all the post-call documentation that comes with it.",
    "Affiliate.com": "Affiliate.com sells performance marketing solutions into advertisers and publishers. Your reps are managing relationship-driven sales cycles where follow-up timing and CRM accuracy directly affect close rates.",
    "Afresh": "Afresh sells fresh inventory optimization software into grocery chains. Your reps are selling into operations and category management teams with complex buying cycles and a lot of post-call admin.",
    "Afternic - a GoDaddy brand": "Afternic sells a domain marketplace platform into brokers and registrars. Your reps are managing high-volume transactional relationships where follow-up consistency is the difference between deals that close and deals that go quiet.",
    "Agility": "Agility sells programmatic advertising solutions into marketing and media buying teams. Your reps are running consultative sales cycles where post-call notes and follow-up are probably still handled manually.",
    "Agility PR Solutions": "Agility PR Solutions sells media monitoring and PR software into communications and marketing teams. Your reps are managing complex evaluation cycles with multiple stakeholders and a significant amount of post-call admin.",
    "Agio": "Agio sells managed IT and cybersecurity services into financial services firms. Trust and compliance are central to every sale, and your reps are managing detailed follow-up after every client conversation.",
    "Agora": "Agora sells real estate investment management software into asset managers and family offices. Your reps are navigating complex sales cycles where precise follow-up and CRM accuracy are critical.",
    "Agora Data, Inc.": "Agora Data sells financing solutions for auto dealers. Your reps are managing relationship-heavy cycles with dealer principals and finance directors, with a lot of manual admin after every conversation.",
    "AiDASH": "AiDASH sells AI-powered vegetation management software into utilities. Your reps are selling into operations and asset management teams with complex evaluation cycles and detailed post-call documentation.",
    "AiFA Labs": "AiFA Labs sells AI and data services into enterprises. Your reps are running consultative cycles with technical and business stakeholders, and post-call admin is probably eating into selling time.",
    "AiFi Inc.": "AiFi sells autonomous retail technology into grocery and convenience store chains. Your reps are navigating operations and technology buyers with complex evaluations and manual post-call workflows.",
    "AI Squared": "AI Squared sells AI integration tools into enterprises. Your reps are running technical evaluations with data and engineering teams where every stakeholder conversation generates follow-up done by hand.",
    "AIM Consulting Group": "AIM Consulting sells technology consulting services into IT and business leadership. Your reps are managing relationship-driven cycles where CRM accuracy and timely follow-up determine whether deals stay warm.",
    "AIRLINQ": "AIRLINQ sells connected vehicle and IoT solutions into fleet and engineering teams. Your reps are running complex evaluations where post-call documentation and follow-up are probably still done manually.",
    "Aimpoint Digital": "Aimpoint Digital sells analytics and data modernization services into data and technology leadership. Your reps are running consultative cycles with significant post-call admin after every stakeholder conversation.",
    "AirDNA": "AirDNA sells short-term rental market data and analytics into real estate investors and operators. Your reps are managing relationship-driven cycles where follow-up timing and CRM discipline directly affect pipeline.",
    "AirOps": "AirOps sells AI workflow automation into operations teams. Your reps are running evaluations with business and technology buyers where manual post-call admin is slowing down their next conversation.",
    "AirSight": "AirSight sells drone-based inspection technology into utilities and infrastructure companies. Your reps are selling into operations teams with complex evaluations and detailed documentation requirements.",
    "AirWorks": "AirWorks sells drone data processing software into AEC and infrastructure firms. Your reps are navigating technical sales cycles where post-call notes and CRM updates are probably handled manually.",
    "Airspace Link, Inc.": "Airspace Link sells drone airspace management solutions into government and enterprise. Your reps are navigating complex regulatory and procurement processes with significant follow-up after every meeting.",
    "Aivo an Engageware Company": "Aivo sells AI-powered customer engagement solutions into financial services. Your reps are running evaluations with CX and digital transformation teams, with substantial post-call admin between conversations.",
    "Aiwyn": "Aiwyn sells practice automation software into accounting firms. Your reps are selling into operations and managing partner leadership with complex cycles and detailed follow-up after every conversation.",
    "Aizon": "Aizon sells AI-powered manufacturing intelligence into pharma and biotech. Your reps are navigating compliance-heavy evaluations where every stakeholder conversation requires precise documentation and follow-up.",
    "Arionkoder": "Arionkoder sells AI and software development services into product and technology leadership. Your reps are running consultative cycles where manual post-call admin is probably the biggest drag on selling time.",
    "Arkestro": "Arkestro sells predictive procurement software into enterprises. Your reps are navigating procurement and supply chain leadership with long evaluation cycles and significant post-call documentation.",
    "Armada": "Armada sells edge computing infrastructure into remote and industrial environments. Your reps are running complex infrastructure evaluations where post-call follow-up and CRM updates are done manually.",
    "Arrcus, Inc.": "Arrcus sells network operating system software into telcos and cloud providers. Your reps are running deep technical evaluations with networking teams, with a lot of documentation required after every call.",
    "Artisan": "Artisan sells AI-powered sales automation into sales and revenue leadership. Your reps are running evaluations where post-call admin is probably still slowing down their pipeline.",
    "Ascend": "Ascend sells accounts payable automation into finance and operations leadership. Your reps are navigating buying cycles where manual CRM updates and follow-up eat into selling time.",
    "Ascend Analytics": "Ascend Analytics sells energy market analytics into utilities and energy companies. Your reps are selling into trading and planning teams with complex evaluation cycles and detailed post-call documentation.",
    "Ascend Partners Inc.": "Ascend Partners sells technology consulting and staffing services into IT and business leadership. Your reps are managing relationship-driven cycles where follow-up consistency determines whether deals move forward.",
    "Ascend Technologies": "Ascend Technologies sells managed IT services into operations and IT leadership. Your reps are managing relationship-driven cycles where CRM accuracy and timely follow-up directly affect retention and growth.",
    "Ascenda": "Ascenda sells loyalty and rewards technology into banks and fintechs. Your reps are navigating complex enterprise sales cycles with multiple stakeholders and significant post-call admin.",
    "Asentech LLC": "Asentech sells technology solutions into healthcare and life sciences. Your reps are managing compliance-heavy evaluations with clinical and IT buyers, with detailed follow-up required after every conversation.",
    "Asignet Technology DNA": "Asignet sells telecom expense and network management solutions into IT and finance leadership. Your reps are selling into enterprises where manual post-call documentation is probably costing more selling time than it should.",
    "AS Software": "AS Software sells specialized software solutions into technical and operations buyers. Your reps are navigating consultative sales cycles where CRM updates and follow-up are still done manually.",
    "ASI": "ASI sells ERP and business management software into the promotional products industry. Your reps are selling into operations and finance leadership with complex evaluation cycles and post-call admin.",
    "AspireHR": "AspireHR sells SAP HR consulting and implementation services into CHRO and IT leadership. Your reps are managing long complex sales cycles where every stakeholder conversation generates detailed follow-up.",
    "AssureCare LLC": "AssureCare sells care management technology into healthcare payers. Your reps are navigating procurement with clinical, IT, and operations teams, with significant documentation required after every meeting.",
    "Astera": "Astera sells data integration and ETL software into enterprises. Your reps are running evaluations with data engineering and analytics teams where post-call admin is probably still handled manually.",
    "Astra Canyon": "Astra Canyon sells IT staffing and consulting services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep deals from going quiet.",
    "Astronomer": "Astronomer sells Apache Airflow-managed infrastructure into data teams. Your reps are running technical evaluations with data engineers and platform teams, with complex post-call documentation after every conversation.",
    "Ativion": "Ativion sells AI-powered business process automation into operations and technology buyers. Your reps are running consultative evaluations where manual post-call admin is slowing down pipeline velocity.",
    "Atlantic": "Atlantic sells workplace technology solutions into IT and facilities leadership. Your reps are navigating complex enterprise sales cycles where CRM discipline and follow-up consistency are critical.",
    "Atrium": "Atrium sells sales performance management and analytics into revenue operations and sales leadership. Your reps are selling into teams that care deeply about data accuracy, and their own CRM is probably far from clean.",
    "Attain": "Attain sells outcomes-based healthcare solutions into clinical and administrative leadership. Your reps are navigating complex procurement cycles with significant follow-up and documentation after every stakeholder conversation.",
    "AU10TIX": "AU10TIX sells identity verification and document authentication technology into compliance, fraud, and digital teams. Your reps are running complex evaluations where post-call admin and CRM updates are done manually.",
    "Auction Software": "Auction Software sells auction platform software into operations and technology buyers. Your reps are managing sales cycles where follow-up timing and CRM accuracy are the difference between closed and lost deals.",
    "AudienceView": "AudienceView sells ticketing and venue management software into entertainment companies. Your reps are selling into operations and marketing leadership with complex cycles and manual post-call workflows.",
    "Augmenta": "Augmenta sells AI-powered electrical design automation into engineering firms. Your reps are running technical evaluations where every stakeholder conversation generates follow-up that is probably still done by hand.",
    "Augury": "Augury sells machine health AI into manufacturing. Your reps are navigating complex evaluations with operations, reliability, and IT teams, with significant post-call documentation required after every meeting.",
    "Aunalytics": "Aunalytics sells data analytics and AI services into financial services and healthcare. Your reps are managing consultative sales cycles where manual CRM updates and follow-up eat into selling time.",
    "Aurascape": "Aurascape sells AI-powered network security solutions into security and networking teams. Your reps are running technical evaluations where post-call admin is probably the biggest drag between calls.",
    "Aureon": "Aureon sells managed IT and technology consulting services into operations and IT leadership. Your reps are managing relationship-driven cycles where CRM accuracy and timely follow-up determine deal momentum.",
    "Aurigo Software Technologies": "Aurigo sells capital program management software into government and infrastructure. Your reps are navigating complex procurement processes with detailed documentation requirements after every stakeholder meeting.",
    "Aurora Solar": "Aurora Solar sells solar design and sales software into solar companies. Your reps are selling into sales and operations leadership where post-call admin is probably slowing down deal velocity.",
    "Austco Healthcare": "Austco Healthcare sells nurse call and clinical communication systems into hospitals. Your reps are navigating clinical, facilities, and IT procurement with detailed follow-up required after every conversation.",
    "Authentic8": "Authentic8 sells secure browser technology into government and enterprise. Your reps are running evaluations with security and compliance teams where manual post-call documentation is a constant drain.",
    "Authentix": "Authentix sells authentication and brand protection solutions into brand, legal, and supply chain teams. Your reps are managing complex cycles where precise follow-up and CRM accuracy are critical to deal progress.",
    "Autify": "Autify sells AI-powered test automation into QA and engineering leadership. Your reps are running technical evaluations where every demo and follow-up conversation generates admin that is probably still done manually.",
    "Autodesk Construction Cloud": "Autodesk Construction Cloud sells construction management software into project managers, VDC, and IT teams. Your reps are navigating complex procurement cycles with significant post-call documentation.",
    "Autonomy": "Autonomy sells autonomous vehicle technology solutions into engineering and operations teams. Your reps are running complex technical evaluations where manual post-call admin is costing selling time.",
    "Autura": "Autura sells towing and roadside management software into municipalities and operators. Your reps are selling into operations leadership where follow-up consistency and CRM accuracy keep deals from stalling.",
    "Ava": "Ava sells AI-powered communication accessibility solutions into HR and DEI leadership. Your reps are running evaluations where every stakeholder conversation generates follow-up that is probably still handled manually.",
    "Avaamo": "Avaamo sells conversational AI and enterprise chatbot solutions into IT, CX, and operations buyers. Your reps are navigating complex evaluations with significant post-call admin after every conversation.",
    "Avaap": "Avaap sells Workday consulting and implementation services into CHRO and IT leadership. Your reps are managing long complex cycles where every discovery and scoping conversation requires detailed documentation.",
    "Avahi": "Avahi sells AI-powered healthcare solutions into clinical, operations, and IT leadership. Your reps are running complex evaluations where post-call documentation and follow-up are probably still done manually.",
    "Avatara": "Avatara sells cloud desktop and managed IT services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy determine deal momentum.",
    "Avertium": "Avertium sells managed security services into CISO and IT leadership. Your reps are building trust through complex security evaluations where every stakeholder conversation requires detailed follow-up.",
    "Aviso AI": "Aviso AI sells AI-powered revenue intelligence into sales and revenue operations leadership. Your reps are running evaluations where ironically the post-call admin is probably still done manually.",
    "Aviture": "Aviture sells custom software development and IT consulting services into technology buyers. Your reps are managing relationship-driven cycles where CRM accuracy and follow-up consistency are critical.",
    "Aviz Networks": "Aviz Networks sells open networking software for data centers into networking and infrastructure teams. Your reps are running deep technical evaluations with significant post-call documentation after every call.",
    "Avo Automation": "Avo Automation sells test automation solutions into QA and engineering leadership. Your reps are running technical evaluations where post-call admin is probably the biggest time sink between conversations.",
    "Avoca": "Avoca sells AI-powered home services dispatch software into operations and franchise leadership. Your reps are managing sales cycles where follow-up timing and CRM discipline directly affect close rates.",
    "Avoma": "Avoma sells AI meeting intelligence and conversation analytics into sales and revenue operations leadership. Your reps are selling into teams that care deeply about call data, and their own post-call admin is probably still manual.",
    "AVIO Consulting": "AVIO Consulting sells MuleSoft integration and API consulting services into technical and business leadership. Your reps are managing complex technical sales cycles with detailed follow-up after every stakeholder conversation.",
    "AVOXI": "AVOXI sells cloud communications and contact center software into IT and CX leadership. Your reps are navigating complex enterprise evaluations where post-call admin and CRM updates are done manually.",
    "Axios HQ": "Axios HQ sells employee communications software into internal communications and HR leadership. Your reps are selling into teams that measure engagement data but probably have messy post-call admin of their own.",
    "Axis Technical Group": "Axis Technical Group sells IT staffing and consulting services into technology and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up is the difference between winning and losing.",
    "AxisCare Home Care Software": "AxisCare sells home care management software into home care agencies. Your reps are selling into operations and clinical leadership where post-call documentation and follow-up are probably still done manually.",
    "Axonify": "Axonify sells frontline employee training and communication software into HR, L&D, and operations buyers. Your reps are navigating complex enterprise evaluations with significant post-call admin after every conversation.",
    "Axuall": "Axuall sells healthcare workforce intelligence and credentialing software into clinical, HR, and IT leadership. Your reps are navigating complex procurement with detailed follow-up required after every stakeholder meeting.",
    "B-Stock": "B-Stock sells a B2B liquidation marketplace platform into supply chain and retail operations teams. Your reps are managing relationship-driven cycles where CRM accuracy and follow-up consistency drive revenue.",
    "BILT Incorporated": "BILT sells digital product instructions technology into product, marketing, and CX teams. Your reps are running evaluations where post-call admin is probably still eating into selling time.",
    "BIS Digital, Inc.": "BIS Digital sells court recording and transcription technology into government. Your reps are navigating public sector procurement processes with detailed documentation requirements after every conversation.",
    "BLAZE®": "BLAZE sells cannabis retail and dispensary management software into operations and ownership groups. Your reps are managing sales cycles where follow-up timing and CRM accuracy determine whether deals close.",
    "BOND.AI": "BOND.AI sells AI-powered personalization for financial services into digital and data leadership at banks. Your reps are running complex evaluations where post-call documentation and follow-up are done manually.",
    "BOSS Solutions": "BOSS Solutions sells ITSM and help desk software into IT and operations leadership. Your reps are running evaluations where every technical demo generates follow-up that is probably still handled manually.",
    "BetterCloud": "BetterCloud sells SaaS operations management into IT operations and security leadership. Your reps are running evaluations where post-call admin and CRM updates are a constant drain on selling time.",
    "Betterworks": "Betterworks sells continuous performance management software into HR and people leadership. Your reps are navigating complex enterprise evaluations with significant post-call admin after every stakeholder conversation.",
    "BevSpot": "BevSpot sells beverage management and inventory software into restaurants. Your reps are selling into operations and ownership groups where fast follow-up after a demo often determines whether a deal closes.",
    "Bevy": "Bevy sells community events management software into community, marketing, and developer relations leadership. Your reps are managing sales cycles where follow-up consistency and CRM accuracy are critical.",
    "Beyond Limits": "Beyond Limits sells industrial AI solutions into energy, manufacturing, and healthcare. Your reps are running complex technical evaluations where every stakeholder conversation generates significant post-call admin.",
    "BiblioCommons": "BiblioCommons sells digital experience platforms into public libraries. Your reps are navigating government and institutional procurement processes with detailed documentation and follow-up after every meeting.",
    "Bicycle AI": "Bicycle AI sells AI-powered data analytics for telecom into network and data leadership. Your reps are running technical evaluations where post-call documentation and CRM updates are probably still done manually.",
    "BigMarker": "BigMarker sells webinar and virtual events software into marketing, demand gen, and events leadership. Your reps are managing sales cycles where follow-up timing and CRM discipline directly affect pipeline.",
    "BigPanda": "BigPanda sells AIOps and event correlation software into IT operations. Your reps are running evaluations with NOC and ITOps leadership where every technical demo generates detailed post-call admin.",
    "BigTime Software, Inc.": "BigTime Software sells professional services automation into operations and finance leadership at consulting firms. Your reps are navigating complex buying cycles with significant post-call documentation.",
    "Bik.ai": "Bik.ai sells conversational commerce and customer engagement AI into CX and digital leadership. Your reps are running evaluations where post-call admin is probably the biggest drag on selling time.",
    "BiltOn": "BiltOn sells construction project management technology into operations and project management leadership. Your reps are managing sales cycles where CRM accuracy and timely follow-up keep deals from stalling.",
    "BirchStreet": "BirchStreet sells procure-to-pay and expense management software into hospitality finance and operations leadership. Your reps are navigating complex evaluations with significant post-call documentation requirements.",
    "BitTitan": "BitTitan sells cloud migration automation for MSPs into technical and business leadership. Your reps are managing partner-driven cycles where follow-up consistency and CRM accuracy directly affect close rates.",
    "Bitmovin": "Bitmovin sells video encoding and streaming infrastructure into engineering and media operations teams. Your reps are running deep technical evaluations where manual post-call admin is a constant drain.",
    "Bits In Glass": "Bits In Glass sells Microsoft technology consulting and solutions into IT and business leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy determine deal momentum.",
    "Bitsclan IT Solutions": "Bitsclan sells software development and IT outsourcing services into technology and product leadership. Your reps are managing consultative cycles where post-call admin is probably still done manually.",
    "Bizzabo": "Bizzabo sells event management and marketing software into events, marketing, and demand gen leadership. Your reps are navigating evaluation cycles with significant post-call admin after every stakeholder conversation.",
    "BizzyCar": "BizzyCar sells automotive digital retailing software into dealerships. Your reps are selling into sales and general management leadership where fast follow-up after a demo often determines whether a deal closes.",
    "Black Box Intelligence™": "Black Box Intelligence sells restaurant performance analytics into operations and finance leadership at restaurant groups. Your reps are managing cycles where CRM accuracy and follow-up consistency drive pipeline.",
    "Blancco Technology Group": "Blancco sells data erasure and IT asset disposition software into IT, security, and compliance teams. Your reps are running evaluations where every technical discussion generates post-call admin done manually.",
    "Blazeo": "Blazeo sells AI-powered sales acceleration solutions into sales and revenue leadership. Your reps are running evaluations where ironically the post-call admin between demos is probably still done by hand.",
    "BlinkOps": "BlinkOps sells security automation and SOAR solutions into security operations teams. Your reps are running technical evaluations where post-call documentation and follow-up are probably still handled manually.",
    "Blockdaemon": "Blockdaemon sells blockchain infrastructure and staking services into engineering and digital asset teams. Your reps are running technical evaluations with significant post-call documentation after every conversation.",
    "Blockskye": "Blockskye sells blockchain-based travel and expense management into finance and travel management leadership. Your reps are navigating complex evaluations where CRM accuracy and follow-up consistency are critical.",
    "Bloom Growth™": "Bloom Growth sells business operating system and EOS tools into leadership teams at growing businesses. Your reps are managing sales cycles where timely follow-up and CRM discipline determine whether deals close.",
    "Bloomfire": "Bloomfire sells knowledge management and sales enablement software into sales, marketing, and operations leadership. Your reps are running evaluations where post-call admin is probably still costing them selling time.",
    "BluIP Inc.": "BluIP sells cloud communications and UCaaS solutions into IT and operations leadership. Your reps are managing relationship-driven cycles where CRM accuracy and follow-up consistency keep deals from going quiet.",
    "BluLogix": "BluLogix sells subscription billing and revenue management software into finance and operations leadership. Your reps are navigating complex evaluations where post-call admin and CRM updates are done manually.",
    "Blue Altair": "Blue Altair sells data analytics and AI consulting services into technology and analytics leadership. Your reps are managing consultative cycles where manual post-call admin is probably eating into selling time.",
    "Blue J": "Blue J sells AI-powered tax research and planning tools into tax and legal leadership at accounting firms. Your reps are selling into a methodical buyer that expects precise follow-up after every conversation.",
    "BlueVector AI": "BlueVector AI sells AI-powered network threat detection into security and network operations teams. Your reps are running technical evaluations where every call generates post-call documentation done manually.",
    "Bluehost": "Bluehost sells web hosting and online presence solutions into small businesses and agencies. Your reps are managing high-volume sales cycles where follow-up timing and CRM discipline directly affect conversion.",
    "Boldin": "Boldin sells financial planning software into financial advisory and wealth management leadership. Your reps are managing consultative cycles where precise follow-up and CRM accuracy build trust with cautious buyers.",
    "Bonzo": "Bonzo sells automated follow-up and relationship nurturing software into real estate and mortgage sales leadership. Your reps are selling into teams that care about follow-up, but their own post-call admin is probably manual.",
    "Bosch Software and Digital Solutions": "Bosch Software and Digital Solutions sells IoT and industrial software into engineering and operations teams. Your reps are running complex technical evaluations with detailed post-call documentation required after every call.",
    "Botify": "Botify sells enterprise SEO automation into SEO, digital marketing, and technology leadership at large brands. Your reps are navigating long evaluation cycles with significant post-call admin after every conversation.",
    "Brafton Inc.": "Brafton sells content marketing services into marketing and content leadership teams. Your reps are managing consultative cycles where follow-up consistency and CRM accuracy determine whether deals stay warm.",
    "Brand Networks": "Brand Networks sells social media advertising and marketing technology into digital marketing and media leadership. Your reps are running evaluations where post-call admin is probably still slowing down pipeline.",
    "Branding Brand": "Branding Brand sells mobile commerce and app solutions into retail digital and technology leadership. Your reps are navigating buying cycles where manual CRM updates and follow-up eat into selling time.",
    "Bravo Team Engineering Design & Fabrication": "Bravo Team sells engineering design and fabrication services into technical and procurement teams. Your reps are managing project-driven cycles where precise follow-up and documentation after every conversation are critical.",
    "Breezeway": "Breezeway sells property operations and guest experience software into short-term rental operators. Your reps are selling into operations leadership where fast follow-up after a demo often determines whether a deal closes.",
    "Brevium": "Brevium sells patient recall and reactivation software into medical practices. Your reps are selling into practice management and clinical leadership where consistent follow-up directly affects pipeline.",
    "Bricz": "Bricz sells supply chain technology consulting into supply chain and operations leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are probably still done manually.",
    "Bridgeway Benefit Technologies": "Bridgeway Benefit Technologies sells benefits administration software into HR, benefits, and IT leadership. Your reps are navigating complex evaluations where every stakeholder conversation generates follow-up done by hand.",
    "BriefCam (Now Milestone)": "BriefCam sells video analytics and intelligence software into security and operations leadership. Your reps are running complex evaluations where post-call documentation and CRM accuracy are critical to deal progress.",
    "Bright Pattern": "Bright Pattern sells cloud contact center software into CX, IT, and operations leadership. Your reps are navigating complex enterprise evaluations where manual post-call admin is a constant drag on selling time.",
    "BrightInsight": "BrightInsight sells digital health platform solutions into pharma and medtech. Your reps are navigating complex regulatory and technical evaluations with significant post-call documentation requirements.",
    "Brightidea": "Brightidea sells innovation management software into innovation, R&D, and strategy leadership at enterprises. Your reps are managing consultative cycles where follow-up precision and CRM accuracy build credibility.",
    "Brillion": "Brillion sells AI-powered financial wellness solutions into financial institutions. Your reps are running evaluations with digital and product leadership where post-call admin is probably still done manually.",
    "Britive": "Britive sells cloud privileged access management into security, DevOps, and cloud infrastructure teams. Your reps are running technical evaluations with complex post-call documentation after every conversation.",
    "Broadband Hospitality": "Broadband Hospitality sells managed WiFi and connectivity solutions into hotels. Your reps are selling into IT and operations leadership where CRM accuracy and timely follow-up keep deals from going quiet.",
    "BugendaiTech": "BugendaiTech sells AI, data, and cloud consulting services into technology and digital transformation leadership. Your reps are managing consultative cycles where post-call admin is probably still eating into selling time.",
    "Buildout": "Buildout sells commercial real estate marketing and CRM software into sales and brokerage leadership at CRE firms. Your reps are selling into a CRM-aware buyer, but their own post-call admin is probably still manual.",
    "Bulletproof, a GLI Company": "Bulletproof sells cybersecurity and managed security services into CISO and IT leadership. Your reps are building trust through complex evaluations where every stakeholder conversation requires detailed follow-up.",
    "Burwood Group": "Burwood Group sells technology consulting and managed services into IT and business leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy determine deal momentum.",
    "Bushel": "Bushel sells agtech and grain management software into cooperatives and agribusinesses. Your reps are selling into operations and technology leadership where post-call documentation and follow-up are done manually.",
    "BusinessNext, Americas": "BusinessNext sells CRM and digital transformation software into banking technology and business leadership. Your reps are running complex evaluations where every stakeholder conversation generates significant post-call admin.",
    "BusyBusy by AlignOps": "BusyBusy sells time tracking and workforce management software into construction operations and project management. Your reps are selling into teams where fast follow-up after a demo determines whether deals close.",
    "Buxton": "Buxton sells customer analytics and site selection software into retail and real estate leadership. Your reps are navigating consultative cycles where precise follow-up and CRM accuracy build trust with analytical buyers.",
    "Buzz": "Buzz sells AI-powered sales engagement and outreach software into sales and revenue operations leadership. Your reps are selling into teams that care about efficiency, but their own post-call admin is probably still manual.",
    "Byteridge": "Byteridge sells software development and product engineering services into product and technology leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are done manually.",
    "C5MI": "C5MI sells digital transformation consulting services into operations and technology leadership. Your reps are managing complex consultative cycles where every stakeholder conversation generates follow-up done by hand.",
    "CARDO AI": "CARDO AI sells AI-powered credit risk management solutions into financial services risk and technology leadership. Your reps are running complex evaluations where post-call documentation and CRM accuracy are critical.",
    "CARTO": "CARTO sells spatial analytics and location intelligence software into data, analytics, and GIS leadership. Your reps are running technical evaluations where manual post-call admin is probably costing them selling time.",
    "CAST": "CAST sells software intelligence and technical debt analysis tools into IT, engineering, and CTO leadership. Your reps are running deep technical evaluations with significant post-call documentation after every conversation.",
    "CATALYST": "CATALYST sells sustainability intelligence software into ESG, sustainability, and operations leadership. Your reps are navigating complex evaluations where follow-up precision and CRM accuracy build credibility with methodical buyers.",
    "CDS": "CDS sells document management and workflow solutions into IT and operations leadership. Your reps are selling into teams that care about process efficiency, but post-call admin for their own reps is probably still manual.",
    "CENTRL Inc": "CENTRL sells third-party risk and compliance management into compliance, legal, and procurement leadership. Your reps are navigating complex evaluations where every meeting generates detailed follow-up done manually.",
    "CETDIGIT (Cetrix Cloud Services)": "CETDIGIT sells Salesforce consulting and implementation services into sales ops and technology leadership. Your reps are managing relationship-driven cycles where CRM accuracy and timely follow-up determine deal momentum.",
    "CFO Solutions": "CFO Solutions sells fractional CFO and financial consulting services into finance and executive leadership. Your reps are managing consultative cycles where precise follow-up and documentation build trust with cautious buyers.",
    "CHESA": "CHESA sells automotive dealer management and compliance solutions into dealership management leadership. Your reps are selling into operations where fast follow-up after a demo often determines whether a deal closes.",
    "CHESS Health": "CHESS Health sells substance use disorder digital health solutions into health systems. Your reps are navigating clinical, operations, and IT procurement with detailed documentation required after every stakeholder conversation.",
    "CINC Systems": "CINC Systems sells HOA management and community association software into property management leadership. Your reps are managing sales cycles where CRM accuracy and follow-up consistency keep deals from stalling.",
    "CIO Solutions": "CIO Solutions sells managed IT services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM discipline determine whether accounts stay warm.",
    "CIRA": "CIRA sells DNS security and internet registry services into IT and security leadership at enterprises and government. Your reps are running evaluations with significant post-call documentation after every technical conversation.",
    "CIS": "CIS sells IT managed services and cybersecurity solutions into operations and IT leadership. Your reps are managing relationship-driven cycles where consistent follow-up and CRM accuracy drive pipeline.",
    "CM Labs Simulations": "CM Labs sells heavy equipment simulation training systems into training, operations, and safety leadership. Your reps are navigating procurement processes with detailed follow-up required after every stakeholder conversation.",
    "CODEExitos": "CODEExitos sells software development services into technology and product leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are probably still done manually.",
    "COFENSE": "Cofense sells phishing detection and response solutions into security and IT leadership. Your reps are running evaluations where every technical conversation generates post-call admin that is probably still done by hand.",
    "CONA Services": "CONA Services sells technology shared services into Coca-Cola bottlers. Your reps are navigating complex enterprise technology evaluations with significant documentation and follow-up after every meeting.",
    "CQL (a Shopify Platinum Partner)": "CQL sells Shopify Plus development and e-commerce consulting into digital, marketing, and technology leadership. Your reps are managing consultative cycles where follow-up precision directly affects close rates.",
    "CRAFTSMAN+": "CRAFTSMAN+ sells digital product and experience development services into product and technology leadership. Your reps are running consultative cycles where manual post-call admin is probably eating into selling time.",
    "CRI Advantage": "CRI Advantage sells technology staffing and consulting services into IT and HR leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep opportunities warm.",
    "CRMIT Solutions": "CRMIT Solutions sells Salesforce consulting and implementation services into sales ops and technology leadership. Your reps are managing complex technical cycles where post-call documentation and follow-up are still done manually.",
    "Calibo": "Calibo sells cloud platform engineering and DevOps solutions into platform and engineering leadership. Your reps are running technical evaluations with significant post-call documentation required after every conversation.",
    "CallSource": "CallSource sells call tracking and marketing analytics for automotive dealers into marketing and operations leadership. Your reps are managing sales cycles where fast follow-up and CRM accuracy directly affect close rates.",
    "CalypsoAI": "CalypsoAI sells AI security and trust solutions into security, risk, and AI governance leadership. Your reps are running evaluations where every technical conversation generates post-call admin done manually.",
    "Calyx": "Calyx sells mortgage origination software into technology and operations leadership at mortgage companies. Your reps are navigating complex buying cycles where precise follow-up and CRM accuracy build buyer confidence.",
    "Campfire Interactive": "Campfire Interactive sells CPQ and sales operations software into sales ops, finance, and technology leadership. Your reps are managing cycles with buyers who care about sales efficiency, while their own post-call admin is still manual.",
    "Camphouse": "Camphouse sells film and TV production management software into production and operations leadership at studios. Your reps are managing sales cycles where follow-up timing and CRM discipline determine deal momentum.",
    "Campspot": "Campspot sells campground management and reservation software into outdoor hospitality operations leadership. Your reps are selling into owners and operators where fast follow-up after a demo often closes deals.",
    "Canopy": "Canopy sells practice management software into accounting firms. Your reps are selling into operations and managing partner leadership where every conversation requires precise follow-up and documentation.",
    "Canvas": "Canvas sells field service management software into trades businesses. Your reps are selling into operations and owner leadership where timely follow-up after a demo is often the difference between won and lost.",
    "CapIntel": "CapIntel sells investment proposal and client communication software into wealth management and financial advisor leadership. Your reps are managing consultative cycles with detailed follow-up required after every conversation.",
    "CarNow": "CarNow sells automotive digital retailing and messaging solutions into dealerships. Your reps are selling into sales and technology leadership where fast follow-up after a demo often determines whether a deal closes.",
    "CareerArc": "CareerArc sells social recruiting and employer branding solutions into HR and talent acquisition leadership. Your reps are navigating evaluation cycles where manual post-call admin is probably slowing down deal velocity.",
    "Carefeed": "Carefeed sells senior living communication and engagement software into operations and marketing leadership at communities. Your reps are managing sales cycles where CRM accuracy and timely follow-up keep opportunities warm.",
    "CargoSprint": "CargoSprint sells air cargo payment and data management solutions into operations and finance leadership at freight companies. Your reps are managing sales cycles with significant post-call documentation after every conversation.",
    "CarltonOne": "CarltonOne sells employee recognition and rewards technology into HR and total rewards leadership. Your reps are navigating complex evaluations where follow-up precision and CRM accuracy build credibility with HR buyers.",
    "Case IQ": "Case IQ sells HR case management and investigation software into HR, compliance, and legal leadership. Your reps are managing sales cycles where precise documentation and follow-up after every conversation are expected.",
    "Celestial Systems Inc.": "Celestial Systems sells software development and IT consulting services into technology and operations leadership. Your reps are managing consultative cycles where CRM accuracy and timely follow-up keep deals from stalling.",
    "Centaur.ai": "Centaur.ai sells AI-powered sales coaching and conversation intelligence into sales leadership. Your reps are selling into teams that care about coaching data, but their own post-call admin is probably still manual.",
    "Centercode": "Centercode sells beta testing and customer validation management software into product and engineering leadership. Your reps are running evaluations where every conversation generates follow-up that is probably still done by hand.",
    "CentralReach": "CentralReach sells ABA therapy practice management software into clinical, operations, and billing leadership. Your reps are navigating complex buying cycles with significant post-call documentation after every conversation.",
    "Centre Technologies": "Centre Technologies sells managed IT and cybersecurity services into IT and operations leadership. Your reps are managing relationship-driven cycles where consistent follow-up and CRM accuracy drive pipeline.",
    "Centrical": "Centrical sells employee performance and engagement software into HR, L&D, and operations leadership. Your reps are navigating enterprise evaluations with significant post-call admin after every stakeholder conversation.",
    "Centuria": "Centuria sells technology staffing and solutions into IT and HR leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM discipline keep opportunities warm.",
    "Ceres": "Ceres sells AI-powered food safety and supply chain risk management into quality, operations, and procurement leadership. Your reps are running evaluations with detailed follow-up required after every stakeholder meeting.",
    "Cerio": "Cerio sells enterprise WiFi and networking solutions into IT and network operations leadership. Your reps are running technical evaluations where post-call documentation and CRM updates are probably still done manually.",
    "Certa.ai": "Certa sells third-party onboarding and risk management automation into procurement, compliance, and legal leadership. Your reps are navigating complex evaluations with significant post-call documentation requirements.",
    "CertifID": "CertifID sells wire fraud prevention for real estate transactions into title company and law firm leadership. Your reps are managing sales cycles where precise follow-up and CRM accuracy build trust with risk-averse buyers.",
    "Certified Credit": "Certified Credit sells credit reporting and mortgage verification services into mortgage operations and compliance leadership. Your reps are managing cycles where detailed documentation and follow-up are expected after every conversation.",
    "Certn": "Certn sells background screening and verification software into HR, compliance, and operations leadership. Your reps are navigating evaluation cycles where follow-up consistency and CRM accuracy directly affect deal velocity.",
    "ChargeLab": "ChargeLab sells EV charging station management software into operations and sustainability leadership at property owners. Your reps are managing sales cycles where timely follow-up after a demo often determines whether deals close.",
    "Chartbeat": "Chartbeat sells real-time content analytics for digital publishers into editorial, analytics, and digital leadership. Your reps are managing evaluation cycles where post-call admin is probably still slowing down pipeline.",
    "CharterUP": "CharterUP sells group transportation marketplace solutions into operations and procurement leadership. Your reps are running consultative cycles where follow-up timing and CRM accuracy directly affect close rates.",
    "Chartwell, Inc.": "Chartwell sells research and benchmarking services into retirement and investment industries. Your reps are managing consultative cycles with methodical buyers who expect precise follow-up after every conversation.",
    "Chata.ai": "Chata.ai sells natural language data analytics into data, analytics, and business intelligence leadership. Your reps are running technical evaluations where post-call documentation and CRM updates are done manually.",
    "Chatmeter": "Chatmeter sells local SEO and reputation management for multi-location brands into marketing and digital leadership. Your reps are managing evaluation cycles where follow-up consistency and CRM accuracy keep deals warm.",
    "Check": "Check sells payroll infrastructure and embedded payroll solutions into product and engineering leadership. Your reps are running technical evaluations where every conversation generates post-call admin done manually.",
    "Checkly": "Checkly sells API and end-to-end testing automation into engineering and platform teams. Your reps are running technical evaluations where post-call follow-up and CRM updates are probably still handled manually.",
    "Cheqroom": "Cheqroom sells equipment management and asset tracking software into operations and IT leadership. Your reps are managing sales cycles where timely follow-up and CRM accuracy keep opportunities from going quiet.",
    "Chronosphere": "Chronosphere sells cloud-native observability and monitoring into engineering, DevOps, and platform teams. Your reps are running deep technical evaluations with significant post-call documentation after every conversation.",
    "ChurnZero": "ChurnZero sells customer success and subscription management software into CS, sales, and operations leadership. Your reps are selling into teams that care about retention data, but their own post-call admin is probably still manual.",
    "Cintoo": "Cintoo sells 3D reality capture and digital twin software into AEC engineering and VDC teams. Your reps are running technical evaluations where every conversation generates follow-up that is probably still done by hand.",
    "Circle Cardiovascular Imaging": "Circle Cardiovascular Imaging sells cardiac imaging AI into hospitals. Your reps are navigating clinical, radiology, and IT procurement with detailed documentation required after every stakeholder meeting.",
    "Cirrascale Cloud Services": "Cirrascale sells GPU cloud computing services into AI, research, and infrastructure teams. Your reps are running technical evaluations where post-call documentation and CRM updates are probably still done manually.",
    "Cirrus Systems, Inc.": "Cirrus Systems sells LED lighting and digital display solutions into operations and facilities leadership. Your reps are managing sales cycles where timely follow-up and CRM accuracy determine whether deals progress.",
    "CirrusLabs": "CirrusLabs sells technology consulting and digital transformation services into technology and business leadership. Your reps are managing complex cycles where post-call documentation and follow-up are done manually.",
    "Citylitics Inc.": "Citylitics sells infrastructure market intelligence into business development and strategy leadership at infrastructure companies. Your reps are managing cycles where CRM accuracy and follow-up timing directly affect pipeline.",
    "Civix": "Civix sells government technology solutions into state and local government. Your reps are navigating public sector procurement processes with detailed follow-up and documentation required after every meeting.",
    "Claris, an Apple company": "Claris sells low-code application development tools into IT and business operations leadership. Your reps are running evaluations where every technical conversation generates post-call admin that is probably still done manually.",
    "ClarisHealth": "ClarisHealth sells healthcare compliance and audit management software into compliance, revenue cycle, and IT leadership. Your reps are navigating complex evaluations with significant documentation requirements.",
    "ClassLink": "ClassLink sells identity and access management for K-12 education into district IT and administration. Your reps are navigating institutional procurement processes with detailed follow-up required after every conversation.",
    "ClassWallet": "ClassWallet sells digital wallet and compliance payment solutions into government and education. Your reps are navigating complex procurement processes where manual post-call admin is a constant drag on deal velocity.",
    "Clean Power Research": "Clean Power Research sells solar intelligence and energy analytics into utilities and energy company leadership. Your reps are managing consultative cycles where follow-up precision and CRM accuracy build trust.",
    "ClearDATA": "ClearDATA sells HIPAA-compliant cloud and managed security for healthcare into IT, security, and compliance leadership. Your reps are running evaluations with significant post-call documentation after every conversation.",
    "Clearscale": "Clearscale sells AWS consulting and cloud migration services into IT leadership. Your reps are managing complex technical sales cycles where every stakeholder conversation generates follow-up done manually.",
    "Clearstory": "Clearstory sells construction change order management software into operations and project management leadership. Your reps are managing sales cycles where timely follow-up after a demo often determines whether deals close.",
    "Clearwave Corporation": "Clearwave sells patient intake and insurance verification software into healthcare operations and revenue cycle leadership. Your reps are navigating complex evaluations with detailed documentation after every meeting.",
    "Cleo": "Cleo sells B2B integration and EDI solutions into IT, supply chain, and operations leadership. Your reps are running evaluations where every technical conversation generates post-call admin done by hand.",
    "ClickIT: DevOps & Software Development": "ClickIT sells DevOps and software development outsourcing into technology and product leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are probably still done manually.",
    "Clickatell": "Clickatell sells chat commerce and customer messaging solutions into CX, digital, and marketing leadership. Your reps are running evaluations where manual post-call admin is a constant drag on selling time.",
    "Climavision": "Climavision sells commercial weather intelligence and forecast data into operations and risk management leadership. Your reps are managing consultative cycles where precise follow-up and CRM accuracy build credibility.",
    "ClinicMind": "ClinicMind sells EHR and revenue cycle management for specialty practices into clinical and administrative leadership. Your reps are navigating buying cycles with detailed follow-up required after every stakeholder conversation.",
    "Closinglock": "Closinglock sells wire fraud prevention for real estate closings into title and escrow leadership. Your reps are managing sales cycles where precise follow-up and CRM accuracy build trust with risk-averse buyers.",
    "Cloud Dentistry": "Cloud Dentistry sells dental staffing marketplace solutions into practice management and clinical leadership. Your reps are managing high-volume sales cycles where follow-up timing and CRM discipline directly affect close rates.",
    "Cloud Inventory®": "Cloud Inventory sells mobile inventory and field operations software into operations, IT, and supply chain leadership. Your reps are navigating complex evaluations with significant post-call documentation.",
    "Cloud for Good": "Cloud for Good sells Salesforce nonprofit and higher education consulting into technology leadership. Your reps are managing relationship-driven cycles where CRM accuracy and follow-up consistency keep deals warm.",
    "CloudBolt Software": "CloudBolt sells cloud management and FinOps automation into cloud, IT, and finance leadership. Your reps are running evaluations where every technical conversation generates post-call admin done manually.",
    "CloudEagle.ai": "CloudEagle.ai sells SaaS spend management and optimization into IT, finance, and procurement leadership. Your reps are running evaluations where ironically their own post-call admin is probably still done manually.",
    "CloudLinux": "CloudLinux sells Linux-based server security and stability solutions into hosting company technical leadership. Your reps are managing sales cycles where precise follow-up and CRM accuracy keep deals from going quiet.",
    "CloudPaths": "CloudPaths sells cloud consulting and managed services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM discipline determine deal momentum.",
    "CloudTern Solutions": "CloudTern sells cloud and digital transformation consulting into technology and business leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are probably still done manually.",
    "Cloudelligent": "Cloudelligent sells AWS managed services and cloud consulting into IT and operations leadership. Your reps are managing relationship-driven cycles where follow-up consistency and CRM accuracy drive pipeline.",
    "Cloudpermit": "Cloudpermit sells permitting and licensing software into municipalities. Your reps are navigating government procurement processes with detailed documentation and follow-up required after every stakeholder conversation.",
    "Cloudwick": "Cloudwick sells AWS data and analytics services into data and technology leadership. Your reps are managing consultative cycles where manual post-call admin is probably eating into selling time.",
    "Clozd": "Clozd sells win-loss analysis and competitive intelligence into sales, product, and strategy leadership. Your reps are selling into teams that care about why deals are lost, while their own post-call admin is probably still manual.",
    "Clutch Solutions": "Clutch Solutions sells managed IT and cloud services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep accounts from going quiet.",
    "CoLab Software": "CoLab Software sells engineering collaboration and design review software into engineering and product development teams. Your reps are running technical evaluations with significant post-call documentation after every conversation.",
    "CoStar Real Estate Manager": "CoStar Real Estate Manager sells lease administration and portfolio management software into real estate and finance leadership. Your reps are navigating complex evaluations where follow-up precision builds trust.",
    "Cobalt": "Cobalt sells penetration testing as a service into security, IT, and compliance leadership. Your reps are running evaluations where every technical conversation generates post-call documentation done manually.",
    "CobbleStone Software": "CobbleStone Software sells contract management and CLM solutions into legal, procurement, and operations leadership. Your reps are managing complex evaluations with significant post-call admin after every stakeholder conversation.",
    "Code Upscale": "Code Upscale sells software development outsourcing services into product and technology leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are probably still done manually.",
    "CodeRabbit": "CodeRabbit sells AI-powered code review automation into engineering and DevOps leadership. Your reps are running technical evaluations where every conversation generates post-call admin that is probably still manual.",
    "Coderio": "Coderio sells software development and nearshore IT services into technology and product leadership. Your reps are managing consultative cycles where follow-up consistency and CRM accuracy keep deals warm.",
    "CodiLime": "CodiLime sells network software development and consulting services into engineering leadership. Your reps are managing complex technical cycles where post-call documentation and follow-up are done manually.",
    "Codingscape": "Codingscape sells software development outsourcing services into product and technology leadership. Your reps are managing consultative cycles where manual post-call admin is probably the biggest drain on selling time.",
    "Codup": "Codup sells software development and digital product services into technology and operations leadership. Your reps are managing consultative cycles where post-call documentation and follow-up are still done manually.",
    "Codvo.ai": "Codvo.ai sells AI and data product engineering services into technology and data leadership. Your reps are managing consultative cycles where every client conversation generates follow-up that is probably still handled manually.",
    "Coefficient": "Coefficient sells spreadsheet automation and data integration tools into revenue operations and data leadership. Your reps are selling into teams that care about data efficiency, but their own CRM is probably still updated manually.",
    "Cognaize": "Cognaize sells AI-powered financial document intelligence into finance, operations, and technology leadership. Your reps are running complex evaluations where post-call documentation and CRM accuracy are critical.",
    "Cognosos, Inc.": "Cognosos sells real-time location and asset tracking for hospitals into facilities, operations, and IT leadership. Your reps are navigating complex procurement with detailed documentation required after every meeting.",
    "Cognota": "Cognota sells learning operations software into L&D and HR leadership. Your reps are managing evaluation cycles where follow-up precision and CRM accuracy build credibility with process-oriented buyers.",
    "Coherent": "Coherent sells insurance calculation and legacy modernization software into actuarial and IT leadership. Your reps are running complex evaluations with significant post-call documentation required after every conversation.",
    "CoinList": "CoinList sells crypto token launch and compliance services into project and executive leadership. Your reps are managing relationship-driven cycles where follow-up timing and CRM discipline directly affect deal progress.",
    "Collective[i]": "Collective[i] sells AI-powered sales forecasting and CRM automation into sales and revenue operations leadership. Your reps are selling into teams that care about forecast accuracy, but their own post-call admin is probably still manual.",
    "Colossal, LLC": "Colossal sells IT and technology services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep accounts from going quiet.",
    "ComTec Solutions": "ComTec Solutions sells technology products and services into IT and procurement leadership. Your reps are managing relationship-driven cycles where consistent follow-up and CRM discipline drive pipeline.",
    "Comm100": "Comm100 sells omnichannel customer engagement and chat software into CX, IT, and operations leadership. Your reps are navigating complex enterprise evaluations where post-call admin is probably still done manually.",
    "CommerceCX": "CommerceCX sells Salesforce CPQ and revenue operations consulting into sales ops and technology leadership. Your reps are managing cycles where buyers care about sales efficiency, while their own post-call admin is still manual.",
    "Commit Consulting": "Commit Consulting sells IT consulting and staffing services into technology and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep deals from stalling.",
    "Comnet": "Comnet sells fiber networking and communications technology for critical infrastructure into operations and IT leadership. Your reps are running technical evaluations with detailed documentation required after every conversation.",
    "ComplyAuto": "ComplyAuto sells automotive compliance management software into dealership management and compliance leadership. Your reps are managing cycles where CRM accuracy and follow-up consistency determine whether deals progress.",
    "ComplyWorks a Veriforce Product": "ComplyWorks sells supply chain compliance and contractor management into procurement, safety, and operations leadership. Your reps are navigating complex evaluations with significant post-call documentation.",
    "Computan": "Computan sells HubSpot and marketing operations consulting into marketing and RevOps leadership. Your reps are managing consultative cycles where follow-up precision and CRM accuracy keep deals warm.",
    "Computer Modelling Group": "Computer Modelling Group sells reservoir simulation software into energy company engineering and operations leadership. Your reps are running deep technical evaluations with significant post-call documentation after every conversation.",
    "Computer Solutions": "Computer Solutions sells IT products and managed services into IT and procurement leadership. Your reps are managing relationship-driven cycles where consistent follow-up and CRM discipline drive pipeline.",
    "ComputerLand of Silicon Valley": "ComputerLand of Silicon Valley sells IT products and services into IT and procurement leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep accounts from going quiet.",
    "Concentric AI": "Concentric AI sells autonomous data security and risk management into security and data leadership. Your reps are running technical evaluations where every conversation generates post-call documentation done manually.",
    "Concetto Labs : Microsoft Solutions Partner": "Concetto Labs sells Microsoft solutions and software development into technology and operations leadership. Your reps are managing consultative cycles where post-call admin and follow-up are probably still done manually.",
    "Concord": "Concord sells contract lifecycle management software into legal, procurement, and operations leadership. Your reps are managing complex evaluations where post-call documentation and follow-up are done manually.",
    "Concord Technologies": "Concord Technologies sells cloud fax and document delivery solutions into IT and operations leadership. Your reps are managing sales cycles where follow-up consistency and CRM accuracy keep deals from going quiet.",
    "Condor": "Condor sells strategic financial planning software into finance and FP&A leadership. Your reps are selling into methodical buyers who expect precise follow-up and documentation after every conversation.",
    "Conduktor": "Conduktor sells Apache Kafka management and data streaming solutions into engineering and data platform teams. Your reps are running deep technical evaluations with significant post-call documentation required.",
    "Conexiant": "Conexiant sells B2B media and marketing services into marketing and business development leadership. Your reps are managing consultative cycles where follow-up timing and CRM accuracy directly affect close rates.",
    "Conexiom": "Conexiom sells sales order automation and EDI solutions into operations, IT, and supply chain leadership. Your reps are running evaluations where every technical conversation generates post-call admin done by hand.",
    "Conexon Connect": "Conexon Connect sells rural broadband and fiber consulting into cooperative and utility leadership. Your reps are navigating institutional procurement processes with detailed documentation required after every meeting.",
    "Conexus Solutions, Inc.": "Conexus Solutions sells IT infrastructure and managed services into IT and operations leadership. Your reps are managing relationship-driven cycles where timely follow-up and CRM accuracy keep deals from stalling.",
    "Confiant Inc": "Confiant sells ad security and quality solutions into ad ops and publisher leadership. Your reps are managing sales cycles where post-call follow-up and CRM accuracy determine whether deals progress.",
    "Courier Health": "Courier Health sells life sciences CRM and field force solutions into commercial operations and sales leadership at pharma companies. Your reps are managing field sales cycles with significant post-call documentation requirements.",
    "Coursedog": "Coursedog sells academic operations software into higher education registrar, provost, and IT leadership. Your reps are navigating institutional procurement with detailed follow-up required after every stakeholder conversation.",
    "Courser": "Courser sells learning management and corporate training solutions into L&D and HR leadership. Your reps are managing evaluation cycles where follow-up consistency and CRM accuracy build credibility with process buyers.",
    "Cova Software": "Cova Software sells cannabis retail point-of-sale and compliance software into operations and ownership groups. Your reps are managing sales cycles where timely follow-up after a demo often determines whether deals close.",
    "Cove": "Cove sells workplace management and office experience software into real estate, IT, and operations leadership. Your reps are navigating complex evaluations where post-call admin is probably still slowing down deal velocity.",
    "Craftable": "Craftable sells restaurant procurement and inventory management software into operations and finance leadership at restaurant groups. Your reps are managing cycles where fast follow-up after a demo often closes deals.",
    "CrashPlan": "CrashPlan sells endpoint backup and cybersecurity solutions into IT and security leadership. Your reps are running evaluations where every technical conversation generates post-call documentation done manually.",
    "Creative Realities, Inc.": "Creative Realities sells digital signage and marketing technology into retail and hospitality marketing and operations leadership. Your reps are navigating complex evaluations with significant post-call admin.",
    "CreatorIQ": "CreatorIQ sells influencer marketing and creator intelligence software into marketing and brand leadership. Your reps are running evaluations where post-call documentation and CRM accuracy are probably still handled manually.",
    "Crelate": "Crelate sells recruiting and staffing CRM software into operations and recruitment leadership at staffing firms. Your reps are selling into buyers who understand CRM well, but their own post-call admin is probably still manual.",
    "Cresta": "Cresta sells AI-powered contact center intelligence into CX, operations, and technology leadership. Your reps are running complex enterprise evaluations where post-call documentation and follow-up are done manually.",
    "Crisp": "Crisp sells food supply chain data and retail analytics into supply chain, sales, and operations leadership at CPG brands. Your reps are managing consultative cycles where follow-up precision builds credibility.",
    "Criteria Corp": "Criteria Corp sells pre-employment assessment and HR analytics software into HR and talent acquisition leadership. Your reps are navigating evaluation cycles where manual post-call admin is probably slowing deal velocity.",
    "Criterion HCM": "Criterion HCM sells HCM and payroll software into HR and finance leadership at mid-market companies. Your reps are managing evaluation cycles where follow-up consistency and CRM accuracy keep deals from stalling.",
    "Crossbeam": "Crossbeam sells partner ecosystem and account mapping software into partnerships and sales leadership. Your reps are managing consultative cycles where post-call follow-up and CRM updates are probably still done manually.",
    "Crosschq": "Crosschq sells recruitment intelligence and reference checking software into talent acquisition and HR leadership. Your reps are managing evaluation cycles where timely follow-up and CRM accuracy keep deals warm.",
    "Crossfuze": "Crossfuze sells ServiceNow consulting and implementation services into IT and operations leadership. Your reps are managing complex technical cycles where every stakeholder conversation generates follow-up done manually.",
    "Crossvale": "Crossvale sells OpenShift and Kubernetes consulting services into DevOps and platform engineering teams. Your reps are running technical evaluations where post-call documentation and follow-up are probably still manual.",
    "Crownpeak": "Crownpeak sells digital experience platform and content management into digital, marketing, and IT leadership. Your reps are navigating complex enterprise evaluations with significant post-call admin after every conversation.",
    "Cryptio": "Cryptio sells crypto accounting and financial reporting software into finance and compliance leadership at digital asset companies. Your reps are managing cycles where precise follow-up and CRM accuracy build trust.",
    "asTech - Driven by Repairify": "asTech sells remote diagnostic and ADAS calibration solutions into auto repair shops. Your reps are selling into operations and technical leadership where fast follow-up after a demo often determines whether deals close.",
    "automotiveMastermind Inc.": "automotiveMastermind sells predictive analytics and marketing automation into dealership sales and marketing leadership. Your reps are managing cycles where CRM accuracy and follow-up consistency drive revenue.",
    "binah.ai": "Binah.ai sells vital signs measurement AI using smartphone cameras into digital health and insurance leadership. Your reps are running technical evaluations where post-call documentation and follow-up are done manually.",
    "boostr": "Boostr sells media sales management and CRM software into sales operations and revenue leadership at media companies. Your reps are selling into CRM-aware buyers, but their own post-call admin is probably still manual.",
    "cerebre": "Cerebre sells cognitive health assessment technology into clinical and research leadership. Your reps are running evaluations where every conversation generates detailed follow-up that is probably still done by hand.",
}

# ─── Persona-specific templates ───────────────────────────────────────────────
PERSONA_LINE3 = {
    "Sales/CRO": "ASPR is an execution layer on top of your CRM with 10+ specialized agents running inside Slack: pre-call research, post-call summaries, CRM updates, deal briefs, and rep coaching. Your team hits higher revenue capacity without adding headcount, and new reps reach full quota in half the normal ramp time.",
    "Manager/Director": "ASPR sits as an execution layer on top of your CRM inside Slack. The moment a call ends, 10+ agents handle the rest: summary written, CRM updated, follow-up drafted. Teams get 25+ hours back per rep per week without changing how anyone works.",
    "Rev ops": "ASPR runs as an execution layer on top of your CRM inside Slack. Every call automatically generates a summary, updates the CRM, and drafts follow-up. Your ops team gets clean pipeline data without chasing reps, and reps get time back to sell.",
}

PERSONA_LINE4 = {
    "Sales/CRO": "Worth 20 minutes to see what it looks like at your scale? aspr.ai",
    "Manager/Director": "Worth 20 minutes? aspr.ai",
    "Rev ops": "Worth 20 minutes to see how it works? aspr.ai",
}

PERSONA_SUBJECT_HOOK = {
    "Sales/CRO": "revenue capacity without adding headcount",
    "Manager/Director": "what would your reps do with 25 extra hours a week",
    "Rev ops": "clean CRM data without chasing your reps",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def clean_dashes(text):
    text = text.replace('—', '.').replace('–', '.').replace('--', '.')
    text = re.sub(r'\s+\.', '.', text)
    return text

def split_two_sentences(text):
    """Split at the first period followed by a space."""
    idx = text.find('. ')
    if idx > 0:
        return text[:idx+1].strip(), text[idx+2:].strip()
    return text, ""

def get_line1(company, employees):
    if company in COMPANY_LINE1:
        return COMPANY_LINE1[company]
    size = int(employees) if employees and employees.isdigit() else 100
    if size < 100:
        return f"{company} is a growing technology company where your reps are managing consultative sales cycles. Every stakeholder conversation generates follow-up that is probably still done manually."
    elif size < 300:
        return f"{company} is a mid-size technology company where your reps are running complex sales cycles with multiple stakeholders. Post-call admin is probably the biggest drag on selling time."
    else:
        return f"{company} is a scaling technology company where your reps are managing enterprise sales cycles with technical, business, and procurement teams. Manual post-call documentation is a constant drain on rep capacity."

def normalize_persona(persona):
    p = persona.strip()
    if p in PERSONA_LINE3:
        return p
    if 'rev ops' in p.lower() or 'revops' in p.lower() or 'revenue ops' in p.lower():
        return 'Rev ops'
    if 'cro' in p.lower() or 'vp' in p.lower() or 'chief' in p.lower():
        return 'Sales/CRO'
    return 'Manager/Director'

# ─── Column mapping ────────────────────────────────────────────────────────────
COL = {
    'Segment': 0, 'First Name': 1, 'Last Name': 2, 'Title': 3,
    'Persona': 4, 'Relevancy': 5, 'Company': 6, 'Email': 7,
    'Employees': 8, 'Emp.Size': 9, 'Industry-Relevancy': 10,
    'Industry': 11, 'Person Linkedin Url': 12, 'Website': 13,
    'Company Linkedin Url': 14, 'City': 15, 'State': 16,
    'Country': 17, 'Company City': 18, 'Company State': 19,
    'Company Country': 20, 'LinkedIn URL': 21
}

# ─── Main ──────────────────────────────────────────────────────────────────────
input_file = '/Users/nac/Documents/ASPR AI/627-1250 - Sheet1.csv'
output_file = '/Users/nac/Documents/ASPR AI/aspr-627-1250-import.csv'

output_rows = []
errors = []
dash_violations = []

with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    rows = list(reader)

for i, row in enumerate(rows):
    try:
        if len(row) < 14:
            errors.append(f"Row {i+1}: too short ({len(row)} cols)")
            continue

        fname    = row[COL['First Name']].strip()
        lname    = row[COL['Last Name']].strip()
        email    = row[COL['Email']].strip()
        company  = row[COL['Company']].strip()
        title    = row[COL['Title']].strip()
        persona  = normalize_persona(row[COL['Persona']])
        employees= row[COL['Employees']].strip()
        city     = row[COL['City']].strip()
        state    = row[COL['State']].strip()
        country  = row[COL['Country']].strip()
        website  = row[COL['Website']].strip()
        linkedin = row[COL['Person Linkedin Url']].strip() if len(row) > 12 else ''

        if not email or not fname or not company:
            errors.append(f"Row {i+1}: missing required field")
            continue

        raw_company_line = clean_dashes(get_line1(company, employees))
        line1, line2 = split_two_sentences(raw_company_line)
        line3 = clean_dashes(PERSONA_LINE3[persona])
        line4 = clean_dashes(PERSONA_LINE4[persona])
        subject = f"{fname}, {PERSONA_SUBJECT_HOOK[persona]}"

        for field, val in [('subject', subject), ('line1', line1), ('line2', line2), ('line3', line3), ('line4', line4)]:
            if '—' in val or '–' in val or '--' in val:
                dash_violations.append(f"Row {i+1} {company} {field}: {val}")

        output_rows.append({
            'First Name': fname,
            'Last Name': lname,
            'Email': email,
            'Company': company,
            'Job Title': title,
            'City': city,
            'State': state,
            'Country': country,
            'Website': website,
            'LinkedIn': linkedin,
            'Subject': subject,
            'First Line(Body)': line1,
            'Second Line(Body)': line2,
            'Third Line(Body)': line3,
            'Fourth Line(Body)': line4,
        })

    except Exception as e:
        errors.append(f"Row {i+1}: {e}")

fieldnames = ['First Name','Last Name','Email','Company','Job Title','City','State','Country','Website','LinkedIn','Subject','First Line(Body)','Second Line(Body)','Third Line(Body)','Fourth Line(Body)']

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"Output rows: {len(output_rows)}")
print(f"Errors: {len(errors)}")
print(f"Dash violations: {len(dash_violations)}")
if errors:
    print("Errors:", errors[:5])
print(f"Saved to: {output_file}")
