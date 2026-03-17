--
-- PostgreSQL database dump
--

\restrict qfCfLbJ4PC4nhCBEjYYSzr989oD6NtA8a4z9hULGdMnGSkOAsuL6P1dWehb7O1D

-- Dumped from database version 15.17
-- Dumped by pg_dump version 15.17

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_logs; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.activity_logs (
    id integer NOT NULL,
    user_id integer,
    user_name character varying(100),
    incident_code character varying(30),
    incident_title character varying(255),
    action character varying(100) NOT NULL,
    detail text,
    team character varying(100),
    report_type character varying(50),
    created_at timestamp without time zone
);


ALTER TABLE public.activity_logs OWNER TO sguard_user;

--
-- Name: activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.activity_logs_id_seq OWNER TO sguard_user;

--
-- Name: activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.activity_logs_id_seq OWNED BY public.activity_logs.id;


--
-- Name: alert_keywords; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.alert_keywords (
    keyword character varying(50) NOT NULL,
    response text,
    severity character varying(20) DEFAULT 'NORMAL'::character varying,
    hit_count integer DEFAULT 0
);


ALTER TABLE public.alert_keywords OWNER TO sguard_user;

--
-- Name: incidents; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.incidents (
    id integer NOT NULL,
    code character varying(30),
    title character varying(255) NOT NULL,
    description text,
    severity character varying(20),
    status character varying(30),
    incident_type character varying(20),
    assigned_to character varying(100),
    source_sms_id integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.incidents OWNER TO sguard_user;

--
-- Name: incidents_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.incidents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.incidents_id_seq OWNER TO sguard_user;

--
-- Name: incidents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.incidents_id_seq OWNED BY public.incidents.id;


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.organizations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    parent_id integer,
    depth integer,
    sort_order integer,
    code character varying(50)
);


ALTER TABLE public.organizations OWNER TO sguard_user;

--
-- Name: organizations_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.organizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.organizations_id_seq OWNER TO sguard_user;

--
-- Name: organizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.organizations_id_seq OWNED BY public.organizations.id;


--
-- Name: received_messages; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.received_messages (
    id integer NOT NULL,
    sender character varying(20),
    message text,
    "timestamp" timestamp without time zone,
    keyword_detected boolean,
    response_message text,
    read boolean
);


ALTER TABLE public.received_messages OWNER TO sguard_user;

--
-- Name: received_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.received_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.received_messages_id_seq OWNER TO sguard_user;

--
-- Name: received_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.received_messages_id_seq OWNED BY public.received_messages.id;


--
-- Name: reset_verifications; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.reset_verifications (
    id integer NOT NULL,
    email character varying(100),
    code character varying(10),
    created_at timestamp without time zone,
    is_verified boolean
);


ALTER TABLE public.reset_verifications OWNER TO sguard_user;

--
-- Name: reset_verifications_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.reset_verifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reset_verifications_id_seq OWNER TO sguard_user;

--
-- Name: reset_verifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.reset_verifications_id_seq OWNED BY public.reset_verifications.id;


--
-- Name: sms_history; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.sms_history (
    id integer NOT NULL,
    recipient character varying(20),
    message text,
    sent_at timestamp without time zone,
    status character varying(20)
);


ALTER TABLE public.sms_history OWNER TO sguard_user;

--
-- Name: sms_history_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.sms_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sms_history_id_seq OWNER TO sguard_user;

--
-- Name: sms_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.sms_history_id_seq OWNED BY public.sms_history.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(100) NOT NULL,
    name character varying(100) NOT NULL,
    password_hash character varying(256),
    role character varying(50),
    auth_provider character varying(30),
    created_at timestamp without time zone,
    is_active boolean,
    company character varying(100),
    employee_id character varying(50),
    phone character varying(20),
    honbu character varying(100),
    team character varying(100),
    part character varying(100),
    token character varying(256)
);


ALTER TABLE public.users OWNER TO sguard_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO sguard_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: warroom_attachments; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.warroom_attachments (
    id integer NOT NULL,
    incident_id character varying(50),
    filename character varying(255),
    original_name character varying(255),
    file_type character varying(50),
    url character varying(500),
    uploaded_by character varying(100),
    "timestamp" timestamp without time zone
);


ALTER TABLE public.warroom_attachments OWNER TO sguard_user;

--
-- Name: warroom_attachments_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.warroom_attachments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.warroom_attachments_id_seq OWNER TO sguard_user;

--
-- Name: warroom_attachments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.warroom_attachments_id_seq OWNED BY public.warroom_attachments.id;


--
-- Name: warroom_chats; Type: TABLE; Schema: public; Owner: sguard_user
--

CREATE TABLE public.warroom_chats (
    id integer NOT NULL,
    incident_id character varying(50),
    sender character varying(50),
    role character varying(50),
    type character varying(20),
    text text,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.warroom_chats OWNER TO sguard_user;

--
-- Name: warroom_chats_id_seq; Type: SEQUENCE; Schema: public; Owner: sguard_user
--

CREATE SEQUENCE public.warroom_chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.warroom_chats_id_seq OWNER TO sguard_user;

--
-- Name: warroom_chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sguard_user
--

ALTER SEQUENCE public.warroom_chats_id_seq OWNED BY public.warroom_chats.id;


--
-- Name: activity_logs id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.activity_logs ALTER COLUMN id SET DEFAULT nextval('public.activity_logs_id_seq'::regclass);


--
-- Name: incidents id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.incidents ALTER COLUMN id SET DEFAULT nextval('public.incidents_id_seq'::regclass);


--
-- Name: organizations id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.organizations ALTER COLUMN id SET DEFAULT nextval('public.organizations_id_seq'::regclass);


--
-- Name: received_messages id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.received_messages ALTER COLUMN id SET DEFAULT nextval('public.received_messages_id_seq'::regclass);


--
-- Name: reset_verifications id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.reset_verifications ALTER COLUMN id SET DEFAULT nextval('public.reset_verifications_id_seq'::regclass);


--
-- Name: sms_history id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.sms_history ALTER COLUMN id SET DEFAULT nextval('public.sms_history_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: warroom_attachments id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.warroom_attachments ALTER COLUMN id SET DEFAULT nextval('public.warroom_attachments_id_seq'::regclass);


--
-- Name: warroom_chats id; Type: DEFAULT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.warroom_chats ALTER COLUMN id SET DEFAULT nextval('public.warroom_chats_id_seq'::regclass);


--
-- Data for Name: activity_logs; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.activity_logs (id, user_id, user_name, incident_code, incident_title, action, detail, team, report_type, created_at) FROM stdin;
8	\N	조경훈	INC-1773561823043	[NEW] 1544-7000 장애 대응	War-Room 참여	조경훈이 INC-1773561823043 War-Room에 참여	\N	AI 리포트	2026-03-15 08:04:31.44737
9	\N	System	INC-1773562622406	CRITICAL: batch server CPU utilization reached 99%	War-Room 개설	새로운 War-Room (INC-1773562622406)이 개설되었습니다.	\N	시스템	2026-03-15 08:17:02.413725
\.


--
-- Data for Name: alert_keywords; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.alert_keywords (keyword, response, severity, hit_count) FROM stdin;
장애	장애 알림이 감지되었습니다. S-Guard AI 시스템에 자동 등록되었습니다.	NORMAL	0
CRITICAL	긴급 장애가 감지되었습니다. 즉시 War-Room을 통해 확인해주세요.	NORMAL	0
오류	시스템 오류가 감지되었습니다. AI 분석을 시작합니다.	NORMAL	0
DOWN	서비스 다운이 감지되었습니다. 긴급 대응팀에 알림을 전송했습니다.	NORMAL	0
비정상	비정상 상태가 감지되었습니다. 자동 분석 중입니다.	NORMAL	0
장애	장애 알림이 감지되었습니다. S-Guard AI 시스템에 자동 등록되었습니다.	NORMAL	0
CRITICAL	긴급 장애가 감지되었습니다. 즉시 War-Room을 통해 확인해주세요.	NORMAL	0
오류	시스템 오류가 감지되었습니다. AI 분석을 시작합니다.	NORMAL	0
DOWN	서비스 다운이 감지되었습니다. 긴급 대응팀에 알림을 전송했습니다.	NORMAL	0
비정상	비정상 상태가 감지되었습니다. 자동 분석 중입니다.	NORMAL	0
장애	장애 알림이 감지되었습니다. S-Guard AI 시스템에 자동 등록되었습니다.	NORMAL	0
CRITICAL	긴급 장애가 감지되었습니다. 즉시 War-Room을 통해 확인해주세요.	NORMAL	0
오류	시스템 오류가 감지되었습니다. AI 분석을 시작합니다.	NORMAL	0
DOWN	서비스 다운이 감지되었습니다. 긴급 대응팀에 알림을 전송했습니다.	NORMAL	0
비정상	비정상 상태가 감지되었습니다. 자동 분석 중입니다.	NORMAL	0
비정상	비정상 상태가 감지되었습니다. 자동 분석 중입니다.	NORMAL	0
\.


--
-- Data for Name: incidents; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.incidents (id, code, title, description, severity, status, incident_type, assigned_to, source_sms_id, created_at, updated_at) FROM stdin;
90	INC-1773562622406	CRITICAL: batch server CPU utilization reached 99%	CRITICAL: batch server CPU utilization reached 99%	CRITICAL	Open	SMS	\N	8	2026-03-15 08:17:02.415644	2026-03-15 08:17:02.415648
89	INC-1773561823043	[NEW] 1544-7000 장애 대응	gateway 504 timeout error in user service	CRITICAL	Open	SMS	\N	7	2026-03-15 08:03:43.074794	2026-03-15 08:03:43.074796
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.organizations (id, name, parent_id, depth, sort_order, code) FROM stdin;
199	임원실	\N	1	0	DIV-001
265	준법지원팀	\N	1	0	DIV-008
266	감사팀	\N	1	0	DIV-007
202	경영부문	\N	1	1	DIV-002
203	경영기획본부	202	2	0	DEP-003
204	경영기획팀	203	3	0	TEA-001
205	재무팀	203	3	1	TEA-002
206	인사팀	203	3	2	TEA-003
207	현지법인	203	3	3	TEA-004
208	경영지원본부	202	2	1	DEP-004
209	품질혁신팀	208	3	0	TEA-005
210	구매계약팀	208	3	1	TEA-006
211	업무지원팀	208	3	2	TEA-007
212	변화추진SAQ	208	3	3	TEA-008
213	미래성장부문	\N	1	2	DIV-003
214	AX본부	213	2	0	DEP-005
215	AI&DATA팀	214	3	0	TEA-009
216	AI운영팀	214	3	1	TEA-010
217	클라우드 본부	213	2	1	DEP-006
218	클라우드사업팀	217	3	0	TEA-011
219	클라우드운영팀	217	3	1	TEA-012
220	그룹클라우드팀	217	3	2	TEA-013
221	개발운영부문	\N	1	3	DIV-004
222	그룹공통본부	221	2	0	DEP-007
223	공통지원팀	222	3	0	TEA-014
224	공통플랫폼팀	222	3	1	TEA-015
225	뱅킹본부	221	2	1	DEP-008
226	뱅킹코어팀	225	3	0	TEA-016
227	뱅킹정보팀	225	3	1	TEA-017
228	뱅킹글로벌팀	225	3	2	TEA-018
229	금융본부	221	2	2	DEP-009
230	카드개발팀	229	3	0	TEA-019
231	상담	230	4	0	PRT-001
232	홈페이지	230	4	1	PRT-002
233	오토금융	230	4	2	PRT-003
234	모바일지원	230	4	3	PRT-004
235	내부관리지원	230	4	4	PRT-005
236	재무정보	230	4	5	PRT-006
237	BD플렛폼지원	230	4	6	PRT-007
238	마케팅	230	4	7	PRT-008
239	포인트	230	4	8	PRT-009
240	데이터비즈	230	4	9	PRT-010
241	통합메시지	230	4	10	PRT-011
242	증권개발팀	229	3	1	TEA-020
243	증권채널팀	229	3	2	TEA-021
244	라이프개발팀	229	3	3	TEA-022
245	DX본부	221	2	3	DEP-010
246	DX추진팀	245	3	0	TEA-023
247	금융DX팀	245	3	1	TEA-024
248	모바일DX팀	245	3	2	TEA-025
249	글로벌DX팀	245	3	3	TEA-026
250	인프라&보안부문	\N	1	4	DIV-005
251	인프라 본부	250	2	0	DEP-011
252	인프라 SRE팀	251	3	0	TEA-027
253	뱅킹IS팀	251	3	1	TEA-028
254	뱅킹정보IS팀	251	3	2	TEA-029
255	뱅킹통신보안팀	251	3	3	TEA-030
256	카드IS팀	251	3	4	TEA-031
257	증권IS팀	251	3	5	TEA-032
258	라이프 IS팀	251	3	6	TEA-033
259	정보보호본부	250	2	1	DEP-012
260	보안컨설팅팀	259	3	0	TEA-034
261	보안사업팀	259	3	1	TEA-035
262	사이버대응팀	259	3	2	TEA-036
263	TFT외부직원	\N	1	5	DIV-006
\.


--
-- Data for Name: received_messages; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.received_messages (id, sender, message, "timestamp", keyword_detected, response_message, read) FROM stdin;
8	1544-7000	CRITICAL: batch server CPU utilization reached 99%	2026-03-15 08:16:27.846917	t	긴급 장애가 감지되었습니다. 즉시 War-Room을 통해 확인해주세요.	f
9	1544-7000	2₩1₩12	2026-03-17 12:12:37.526673	f	\N	f
\.


--
-- Data for Name: reset_verifications; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.reset_verifications (id, email, code, created_at, is_verified) FROM stdin;
\.


--
-- Data for Name: sms_history; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.sms_history (id, recipient, message, sent_at, status) FROM stdin;
1	1544-7000	긴급 장애가 감지되었습니다. 즉시 War-Room을 통해 확인해주세요.	2026-03-15 08:16:27.854242	sent
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.users (id, email, name, password_hash, role, auth_provider, created_at, is_active, company, employee_id, phone, honbu, team, part, token) FROM stdin;
2	test2@shinhan.com	김철수	9462cd273a67ededaa354ae88093897e:ac8687641bf5e09891369320e26799a6eac1d56ff7403d5dec11935b0acfbd0e	analyst	local	2026-03-14 06:35:22.150892	t	신한은행	SH002	010-9999-1111	은행본부	은행개발팀	모바일	\N
1	test@shinhan.com	조경훈(수정)	4fbf9ecf5e577f9028cc0ab5298bde61:00974f73c939aa9409cb0cc624c018dab60efa3e3b1c2387c829b298ff1e56d8	analyst	local	2026-03-14 06:30:53.658547	t	신한은행	SH001	010-0000-0000	금융본부	카드개발팀	모바일	\N
3	khcho0421@gmail.com	조경훈	f19a3e9b0b3d73cfaacafbbc3f28ca07:1f8ac864e2f1677a990eeb9643228d27d8cdce1dee22ef4e3ce81d20eb3eebe0	analyst	local	2026-03-14 06:40:58.804573	t	신한DS	18121020	010-4732-8880	금융본부	카드개발팀	상담	d7361e99aecabeae32d2b0e402f8d971a39a49baadc75fccfc6eceb877ace590
\.


--
-- Data for Name: warroom_attachments; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.warroom_attachments (id, incident_id, filename, original_name, file_type, url, uploaded_by, "timestamp") FROM stdin;
6	INC-1773561823043	4b8bc71246811bfd59e445cf.jpeg	KakaoTalk_Photo_2026-03-15-15-36-39 002.jpeg	image/jpeg	/warroom/uploads/4b8bc71246811bfd59e445cf.jpeg	조경훈	2026-03-15 08:04:20.80674
7	INC-1773562622406	2def5aa7f6d7ac7dcffe87c4.jpeg	KakaoTalk_Photo_2026-03-15-15-36-39 002.jpeg	image/jpeg	/warroom/uploads/2def5aa7f6d7ac7dcffe87c4.jpeg	조경훈	2026-03-15 08:17:17.019415
\.


--
-- Data for Name: warroom_chats; Type: TABLE DATA; Schema: public; Owner: sguard_user
--

COPY public.warroom_chats (id, incident_id, sender, role, type, text, "timestamp") FROM stdin;
65	INC-1773561823043	조경훈	User	file	[첨부파일] KakaoTalk_Photo_2026-03-15-15-36-39 002.jpeg|/warroom/uploads/4b8bc71246811bfd59e445cf.jpeg|image/jpeg	2026-03-15 08:04:20.80786
67	INC-1773561823043	시스템	System	system	👤 조경훈님이 War-Room에 참여하였습니다.	2026-03-15 08:04:31.439753
69	INC-1773562622406	시스템	System	system	[장애발생] 1544-7000로부터 SMS 수신: CRITICAL: batch server CPU utilization reached 99%	2026-03-15 08:17:02.442382
72	INC-1773562622406	조경훈	analyst	me	ㄴㄴ	2026-03-15 08:17:17.03189
66	INC-1773561823043	조경훈	analyst	me	ㅎ2	2026-03-15 08:04:20.835449
68	INC-1773562622406	AI Autopilot	AI분석	ai_analysis	✅ Here's my analysis and response plan as a systems expert:\n\n**Analysis:** The critical alert indicates that the batch server is experiencing extremely high CPU usage, reaching 99%. This could be due to various factors such as inefficient code, insufficient resources, or malicious activity.\n\n**Response Plan:** I will immediately investigate the cause of the high CPU utilization by reviewing system logs, monitori	2026-03-15 08:17:02.433201
70	INC-1773562622406	시스템	System	system	War-Room 채팅방이 생성되었습니다. 모든 대화 내용은 장애 해결 시 AI 학습에 사용됩니다.	2026-03-15 08:17:02.449479
71	INC-1773562622406	조경훈	User	file	[첨부파일] KakaoTalk_Photo_2026-03-15-15-36-39 002.jpeg|/warroom/uploads/2def5aa7f6d7ac7dcffe87c4.jpeg|image/jpeg	2026-03-15 08:17:17.019743
73	INC-1773562622406	조경훈	analyst	me	이건ㄴ	2026-03-15 08:23:05.329659
74	INC-1773562622406	조경훈	analyst	me	뭐지	2026-03-15 08:23:06.95242
63	INC-1773561823043	시스템	System	system	[장애발생] 1544-7000로부터 SMS 수신: gateway 504 timeout error in user service	2026-03-15 08:03:43.089371
64	INC-1773561823043	시스템	System	system	War-Room 채팅방이 생성되었습니다. 모든 대화 내용은 장애 해결 시 AI 학습에 사용됩니다.	2026-03-15 08:03:43.096386
\.


--
-- Name: activity_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.activity_logs_id_seq', 9, true);


--
-- Name: incidents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.incidents_id_seq', 90, true);


--
-- Name: organizations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.organizations_id_seq', 266, true);


--
-- Name: received_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.received_messages_id_seq', 9, true);


--
-- Name: reset_verifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.reset_verifications_id_seq', 8, true);


--
-- Name: sms_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.sms_history_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: warroom_attachments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.warroom_attachments_id_seq', 7, true);


--
-- Name: warroom_chats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sguard_user
--

SELECT pg_catalog.setval('public.warroom_chats_id_seq', 74, true);


--
-- Name: activity_logs activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.activity_logs
    ADD CONSTRAINT activity_logs_pkey PRIMARY KEY (id);


--
-- Name: alert_keywords alert_keywords_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.alert_keywords
    ADD CONSTRAINT alert_keywords_pkey PRIMARY KEY (keyword);


--
-- Name: incidents incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.incidents
    ADD CONSTRAINT incidents_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_code_key; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_code_key UNIQUE (code);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: received_messages received_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.received_messages
    ADD CONSTRAINT received_messages_pkey PRIMARY KEY (id);


--
-- Name: reset_verifications reset_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.reset_verifications
    ADD CONSTRAINT reset_verifications_pkey PRIMARY KEY (id);


--
-- Name: sms_history sms_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.sms_history
    ADD CONSTRAINT sms_history_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: warroom_attachments warroom_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.warroom_attachments
    ADD CONSTRAINT warroom_attachments_pkey PRIMARY KEY (id);


--
-- Name: warroom_chats warroom_chats_pkey; Type: CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.warroom_chats
    ADD CONSTRAINT warroom_chats_pkey PRIMARY KEY (id);


--
-- Name: ix_activity_logs_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_activity_logs_id ON public.activity_logs USING btree (id);


--
-- Name: ix_incidents_code; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE UNIQUE INDEX ix_incidents_code ON public.incidents USING btree (code);


--
-- Name: ix_incidents_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_incidents_id ON public.incidents USING btree (id);


--
-- Name: ix_organizations_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_organizations_id ON public.organizations USING btree (id);


--
-- Name: ix_received_messages_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_received_messages_id ON public.received_messages USING btree (id);


--
-- Name: ix_received_messages_sender; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_received_messages_sender ON public.received_messages USING btree (sender);


--
-- Name: ix_reset_verifications_email; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_reset_verifications_email ON public.reset_verifications USING btree (email);


--
-- Name: ix_reset_verifications_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_reset_verifications_id ON public.reset_verifications USING btree (id);


--
-- Name: ix_sms_history_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_sms_history_id ON public.sms_history USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_warroom_attachments_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_warroom_attachments_id ON public.warroom_attachments USING btree (id);


--
-- Name: ix_warroom_attachments_incident_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_warroom_attachments_incident_id ON public.warroom_attachments USING btree (incident_id);


--
-- Name: ix_warroom_chats_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_warroom_chats_id ON public.warroom_chats USING btree (id);


--
-- Name: ix_warroom_chats_incident_id; Type: INDEX; Schema: public; Owner: sguard_user
--

CREATE INDEX ix_warroom_chats_incident_id ON public.warroom_chats USING btree (incident_id);


--
-- Name: organizations organizations_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sguard_user
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.organizations(id);


--
-- PostgreSQL database dump complete
--

\unrestrict qfCfLbJ4PC4nhCBEjYYSzr989oD6NtA8a4z9hULGdMnGSkOAsuL6P1dWehb7O1D

