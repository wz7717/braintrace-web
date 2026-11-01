"""Bilingual workbench. Frozen inference remains in the isolated queue worker."""
from pathlib import Path
import html
import re
import secrets
import streamlit as st
import streamlit.components.v1 as components
from cloud_service import get_startup
from browser_download import local_download
from startup_runtime import STAGES

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='BrainTrace', page_icon='🧠', layout='wide', initial_sidebar_state='expanded')
st.markdown((ROOT/'web/streamlit.css').read_text(encoding='utf-8'), unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div class="bt-brand">◈ BrainTrace<small>TRANSCRIPTOMIC WORKBENCH</small></div>', unsafe_allow_html=True)
    language = st.radio('Language / 语言', ['中文','English'], horizontal=True, key='ui_language')

def tr(zh, en):
    return en if language == 'English' else zh

def heading(number, zh, en):
    st.markdown(f'<div class="bt-section"><span>{number}</span><h3>{html.escape(tr(zh,en))}</h3></div>', unsafe_allow_html=True)

def show_error(exc, code=None):
    messages = {
        'rate_limit': ('请求过于频繁，请稍后重试。','Too many requests. Please try again later.'),
        'session_expired': ('会话已过期，请开始新会话。','Your session has expired. Start a new session.'),
        'session_rejected': ('会话校验失败，请刷新页面。','Session validation failed. Refresh the page.'),
        'session_job_quota': ('已有排队或运行任务，请等待完成。','A job is already queued or running. Wait for it to finish.'),
        'queue_full': ('任务队列已满，请稍后重试。','The queue is full. Please try again later.'),
        'queue_timeout': ('排队超时，未启动推断，可以重新提交。','Queue timed out before inference started. You may submit again.'),
        'timeout': ('推断超时，任务已停止。','Inference timed out and was stopped.'),
        'capacity': ('服务缓存已满，请稍后重试。','Service capacity is full. Please try again later.'),
        'runtime_unavailable': ('计算服务暂不可用。','The inference service is temporarily unavailable.'),
        'job_expired': ('任务不存在或已过期。','This job is missing or has expired.'),
    }
    code = code or getattr(exc, 'code', '')
    pair = messages.get(code)
    st.error(tr(*pair) if pair else tr('操作未完成，请查看下方错误详情。','The operation did not complete. See the error details below.'))
    with st.expander(tr('错误详情（原始信息）','Error details (original message)'), expanded=True):
        st.code(str(exc), language=None)

with st.sidebar:
    st.caption(tr('参考模型','REFERENCE MODEL'))
    species = st.radio(tr('选择路线','Choose a route'), ['macaque','human'], key='route',
        format_func=lambda x: tr('猕猴 · 三层候选','Macaque · Three tiers') if x=='macaque' else tr('人类 · CEL','Human · CEL'))
    st.divider()
    st.markdown(tr('**工作流程**\n\n01　选择输入\n\n02　排队推断\n\n03　查看候选','**WORKFLOW**\n\n01　Choose input\n\n02　Queue inference\n\n03　Review candidates'))
    st.divider()
    st.caption(tr('无需登录 · 单机排队\n\n当前页面会话独立保存任务。','No sign-in · Single-worker queue\n\nJobs belong to this page session.'))

st.markdown('<div class="bt-eyebrow">SINGLE-SAMPLE ANALYSIS</div>', unsafe_allow_html=True)
st.title(tr('从表达谱，追溯脑区候选','From expression to brain-region candidates'))
st.caption(tr('使用固定参考模型，依次查看 Network、Group 与 Exact；人类路线提供粗粒度候选。',
    'Explore Network, Group and Exact candidates with fixed references. The human route reports coarse brain-region candidates.'))
st.markdown('<div class="bt-steps">'+''.join(f'<div><b>0{i}</b>{html.escape(label)}</div>' for i,label in enumerate(
    [tr('准备输入','Prepare input'),tr('运行推断','Run inference'),tr('解读结果','Interpret results')],1))+'</div>', unsafe_allow_html=True)
st.caption(tr('仅供研究。候选排名不是确定定位或临床诊断；请勿上传含个人身份信息的文件。',
    'Research use only. Candidate rankings are not definitive localization or a clinical diagnosis. Do not upload identifying information.'))

manager = get_startup(ROOT)
initial = manager.snapshot()
stage_names = {
    'cache': ('检查已有环境','Check existing environment'),
    'r': ('准备 R 4.6.1','Prepare R 4.6.1'),
    'r_packages': ('准备四个 R 包','Prepare four R packages'),
    'python': ('准备固定 Python 环境','Prepare pinned Python'),
    'verify': ('确认组件版本','Confirm component versions'),
    'assets': ('载入运行资产','Prepare runtime assets'),
    'ready': ('服务就绪','Service ready'),
}

@st.fragment(run_every=2 if initial['state']!='ready' else None)
def startup_panel():
    state = manager.snapshot()
    if state['state']=='ready' and initial['state']!='ready':
        st.rerun()
    with st.container(border=True, key='startup_panel'):
        if state['state']=='ready':
            st.success(tr('两条路线均已就绪','Both inference routes are ready'))
        else:
            heading('•', '服务启动进度', 'Service startup')
            st.write(tr(*stage_names[state['stage']]))
            st.progress(STAGES.index(state['stage'])/(len(STAGES)-1),
                text=tr('阶段进度；不代表剩余时间','Stage progress; not an estimate of time remaining'))
            a,b=st.columns(2)
            a.metric(tr('本次启动耗时','Startup elapsed'), f"{state['elapsed']//60:02}:{state['elapsed']%60:02}")
            b.metric(tr('距最近日志','Since last log'), f"{state['quiet_seconds']} s")
            if state['state']=='failed':
                st.error(tr('启动失败。已完成的组件保留，可按下方错误修复后重试。','Startup failed. Completed components are retained. Review the error before retrying.'))
                st.code(state['error'], language=None)
                if st.button(tr('复用缓存重试','Retry with cached components'), key='retry_startup', disabled=state['retry_in']>0):
                    manager.start(retry=True); st.rerun()
                if state['retry_in']>0: st.caption(tr(f"{state['retry_in']} 秒后可重试。",f"Retry available in {state['retry_in']} seconds."))
            else:
                st.caption(tr('正在后台准备环境。已安装组件会直接复用；切换语言不会重新启动构建。首次空缓存仍需编译 R，请勿反复重启。',
                    'Environment setup runs in the background. Installed components are reused; switching language does not restart it. An empty cache still requires an R build. Avoid repeated restarts.'))
                if state['quiet_seconds']>90:
                    st.warning(tr('日志暂未更新；编译可能仍在运行，也可能在等待下载。安装总超时为 30 分钟。',
                        'No recent log output. Compilation or a download may still be running. Setup has a 30-minute timeout.'))
        with st.expander(tr('实时安装日志 · 最近 160 行','Live installation log · last 160 lines'), expanded=state['state']!='ready'):
            st.code(state['log'] or tr('等待第一条日志…','Waiting for the first log line…'), language=None)
            st.caption(tr('仅显示环境安装日志，不包含其他访客的输入或结果。完整安装输出也写入云端管理日志。',
                'Environment installation output only; no visitor inputs or results. Full installation output is also written to the cloud console.'))

startup_panel()
if initial['state']!='ready':
    st.info(tr('环境就绪后，输入与结果面板会自动出现。','Input and result panels will appear automatically when the environment is ready.'))
    st.stop()
svc = manager.value
try:
    owner, csrf, cookie = svc.session(st.session_state.get('_anonymous_cookie'))
    st.session_state['_anonymous_cookie'] = cookie
except Exception:
    st.session_state.pop('_anonymous_cookie',None)
    st.session_state.pop('_job',None)
    st.warning(tr('会话已过期，结果与未完成任务不再可用。','The session expired. Previous results and unfinished jobs are no longer available.'))
    if st.button(tr('开始新会话','Start a new session')): st.rerun()
    st.stop()

active = False
if st.session_state.get('_job'):
    try: active = svc.result(owner, st.session_state['_job'])['status'] in ('queued','running')
    except Exception: pass
left,right = st.columns([2.2,1],gap='large')
with left, st.container(border=True, key='input_panel'):
    heading('01', '输入与运行', 'Input and run')
    source = st.radio(tr('输入来源','Input source'), ['upload','example'], horizontal=True, key='input_source',
        format_func=lambda x: tr('上传样本','Upload sample') if x=='upload' else tr('运行现有示例','Run existing example'))
    configs = st.multiselect(tr('冻结配置','Frozen programs'), ['RAW_FIXED','RANK_FIXED'], default=['RAW_FIXED','RANK_FIXED'], key='human_configs') if species=='human' else ['floor_clip']
    uploaded, example, contract = None, None, False
    if source=='upload':
        sample = st.text_input(tr('样本代号','Sample ID'), value='sample_001', max_chars=128, key='sample_id')
        uploaded = st.file_uploader(tr('选择一个样本文件','Choose one sample file'),type=['cel','gz'] if species=='human' else ['npz','csv','tsv'],
            max_upload_size=80 if species=='human' else 8, key='upload_'+species+'_'+str(st.session_state.get('_upload_epoch',0)))
        contract = st.checkbox(tr('我已确认平台、基因标识和归一化符合输入规范。','I confirm the platform, gene identifiers and normalization meet the input contract.'), key='contract_'+species)
    else:
        sample='example'
        example='GSM755211' if species=='human' else st.selectbox(tr('选择示例','Choose an example'),['GSE128537','GSE179328','PsychENCODE_AMY','PsychENCODE_HIP'],key='example_id')
        if species=='human': st.info('GSM755211 · Human Exon 1.0 ST CEL')
        st.caption(tr('此操作会实际运行一个样本；示例真值仅用于结果说明。','This runs one real sample. Example truth labels are used only for interpretation.'))
    st.divider()
    if st.button(tr('提交真实推断 →','Run inference →'), type='primary', disabled=active or not configs, key='run_inference', use_container_width=True):
        try:
            key=secrets.token_urlsafe(20)
            if source=='upload':
                if uploaded is None or not contract:
                    st.warning(tr('请选择样本并确认输入规范。','Choose a sample and confirm the input contract.'))
                elif uploaded.size>(80 if species=='human' else 8)*1024**2:
                    st.error(tr('文件超过当前路线的大小限制。','File exceeds this route’s upload limit.'))
                else:
                    job=svc.submit_upload(owner,csrf,species,sample,uploaded.name,uploaded.getvalue(),configs,key)
                    st.session_state['_job']=job['id']
                    st.session_state['_upload_epoch']=st.session_state.get('_upload_epoch',0)+1
                    st.rerun()
            else:
                job=svc.submit_example(owner,csrf,species,example,configs,key)
                st.session_state['_job']=job['id']; st.rerun()
        except Exception as exc: show_error(exc)
    st.caption(tr('每会话：同时 1 项，30 分钟内最多 4 项。全站：单机排队，最多 8 项活动任务。',
        'Per session: one active job, up to four submissions per 30 minutes. One shared worker; at most eight active jobs globally.'))
with right, st.container(border=True, key='guide_panel'):
    heading('i', '输入指南', 'Input guide')
    if species=='human':
        st.markdown('**Human Exon 1.0 ST**')
        st.write(tr('CEL / CEL.gz · 最大 80 MiB','CEL / CEL.gz · up to 80 MiB'))
        st.caption(tr('固定 RAW / RANK 配置；输出九个粗粒度脑区候选，不提供 Group / Exact。',
            'Fixed RAW / RANK programs; nine coarse brain-region candidates, without Group / Exact.'))
    else:
        st.markdown('**NPZ · CSV · TSV**')
        st.write(tr('单样本 · 最大 8 MiB','Single sample · up to 8 MiB'))
        st.caption(tr('原 5000 / 21668 基因契约；5000 基因输入只运行 Network。PsychENCODE 需指定公共矩阵全部 26,514 行的单样本计数。',
            'Original 5000 / 21668 gene contracts. A 5000-gene input supports Network only. PsychENCODE requires all 26,514 rows of one sample from the designated public matrix.'))
    st.divider()
    st.caption(tr('Group 是候选集合，成员数可不同。Exact 是探索性细区排序。分数不是已校准的定位正确概率。',
        'Group candidates can contain different numbers of regions. Exact is exploratory fine-region ranking. Scores are not calibrated probabilities of correct localization.'))

@st.fragment(run_every=2 if active else None)
def result_panel():
    with st.container(border=True, key='job_panel'):
        heading('02', '任务状态', 'Job status')
        job_id=st.session_state.get('_job')
        if not job_id:
            st.caption(tr('尚未提交任务。准备好输入后，在上方提交推断。','No job submitted. Prepare an input and run inference above.'))
        else:
            try:
                current_owner,_,_=svc.session(st.session_state['_anonymous_cookie'])
                job=svc.result(current_owner,job_id)
            except Exception as exc:
                show_error(exc); return
            if job['status'] in ('queued','running'):
                st.info(tr(f"排队中 · 前方 {job['queue_position']} 项任务",f"Queued · {job['queue_position']} jobs ahead") if job['status']=='queued' else tr('正在运行真实推断','Running inference'))
                st.caption(tr('此面板每 2 秒更新，切换语言不会重复提交。','This panel updates every 2 seconds. Language changes do not resubmit jobs.'))
            elif active: st.rerun()
            elif job['status']=='failed':
                show_error(job['error']['message'],job['error'].get('code'))
                if st.button(tr('准备下一项任务','Prepare next job'),key='after_failure'):
                    st.session_state.pop('_job',None); st.rerun()
            else: st.success(tr('推断完成','Inference completed'))
    with st.container(border=True, key='results_panel'):
        heading('03', '候选结果', 'Candidate results')
        if not job_id or job['status']!='succeeded':
            st.caption(tr('完成推断后，这里显示各层前三名、完整结果与下载。','After inference, review the top three candidates, full output and downloads here.'))
            return
        result=job['result']
        st.text(result['sample_id']+' · '+result['species']+' · '+result['mode'])
        labels=svc.backend.read_json(svc.backend.ROOT/'metadata/human_labels.json') if result['species']=='human' else {}
        views=result.get('tiers',result.get('predictions',{}))
        columns=st.columns(len(views))
        for column,(tier,item) in zip(columns,views.items()):
            with column, st.container(border=True):
                st.markdown('**'+tier+'**')
                if not item.get('ranking'):
                    st.warning(tr('本层不可用','This tier is unavailable'))
                    st.caption(item.get('reason','Unavailable')); continue
                rows=[]
                for rank,cid in enumerate(item['ranking'][:3],1):
                    ix=item['classes'].index(cid)
                    name=labels.get(cid,cid)
                    row={tr('排名','Rank'):rank,tr('候选','Candidate'):name+' ('+cid+')' if name!=cid else cid,tr('分数','Score'):item['scores'][ix]}
                    if 'members' in item: row[tr('成员','Members')]=', '.join(item['members'][ix])
                    rows.append(row)
                def cell(value): return html.escape(str(value)).replace('\\','\\\\').replace('|','\\|').replace('\n',' ')
                headers=list(rows[0])
                st.markdown('\n'.join([' | '.join(headers),' | '.join('---' for _ in headers)]+[' | '.join(cell(row[h]) for h in headers) for row in rows]))
        st.caption(tr('Top 3 覆盖不等于 Top 1 正确；Group 集合命中与 Exact 单标签命中分别解释。',
            'Top 3 coverage does not imply Top 1 correctness. Group set hits and Exact single-label hits have different meanings.'))
        if result.get('warnings'):
            with st.expander(tr('结果说明（原始信息）','Result notes (original messages)')):
                for warning in result['warnings']: st.text(str(warning))
        components.html(local_download(svc.csv(current_owner,job_id),'BrainTrace_scores.csv',tr('下载完整 CSV','Download full CSV')),height=45)
        with st.expander(tr('完整 JSON 结果','Full JSON result')): st.json(result)
        if st.button(tr('准备下一项任务','Prepare next job'),key='after_success'):
            st.session_state.pop('_job',None); st.rerun()
result_panel()

with st.container(border=True, key='resources_panel'):
    heading('04', '示例与资源', 'Examples and resources')
    st.caption(tr('43 种已有候选组合。缺少组合或输入不兼容时，下层会明确标注不可用。',
        '43 existing candidate combinations. Missing combinations or incompatible inputs are explicitly marked unavailable.'))
    choices=svc.backend.read_json(svc.backend.ROOT/'examples/three_tier/EXAMPLES.json')
    c1,c2=st.columns(2,gap='large')
    with c1:
        eid=st.selectbox(tr('下载猕猴输入示例','Download macaque input example'),[x['id'] for x in choices],key='download_example')
        item=next(x for x in choices if x['id']==eid)
        path=svc.backend.ROOT/item['input']
        components.html(local_download(path.read_bytes(),path.name,tr('下载所选示例','Download selected example')),height=40)
    with c2:
        guide=st.selectbox(tr('技术说明（英文原文）','Technical guide (English)'),['INPUT_FORMATS.md','PSYCHENCODE_INPUT.md','MODEL_CARD.md','COVERAGE.md','DATA_AND_LICENSES.md'],key='guide')
    with st.expander(tr('阅读说明','Read guide')):
        guide_text=(svc.backend.ROOT/'docs'/guide).read_text(encoding='utf-8-sig')
        guide_text=re.sub(r'\[([^\]]+)\]\((?!https?://)([^)]+\.md(?:#[^)]*)?)\)',
            lambda m: m.group(1)+' (`'+Path(m.group(2).split('#')[0]).name+'`; '+tr('见说明选择器','see Guide selector')+')',guide_text)
        st.markdown(guide_text)
    st.caption(tr('结果保留 30 分钟，会话最长 2 小时。刷新、断开或重启可能丢失任务。匿名限额按页面会话计算，不能识别自然人。',
        'Results last 30 minutes; sessions last up to two hours. Refresh, disconnect or restart may lose jobs. Anonymous quotas apply to page sessions, not verified individuals.'))
