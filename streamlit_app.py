"""Public anonymous interface; frozen inference runs in a separate pinned worker."""
from pathlib import Path
import re
import secrets
import streamlit as st
import streamlit.components.v1 as components
from cloud_service import get_service
from browser_download import local_download

st.set_page_config(page_title='BrainTrace', page_icon='🧠', layout='wide')
st.title('BrainTrace')
st.caption('Single-sample brain-region candidate ranking · 单样本脑区候选排序')
st.info('研究用途。输出是候选排名，并非确定的脑区定位或临床诊断。请勿上传带有个人身份信息的文件。')

@st.cache_resource
def service():
    return get_service(Path(__file__).resolve().parent)

try:
    with st.spinner('正在准备固定运行环境；首次启动可能需要数分钟。'):
        svc = service()
except Exception as exc:
    st.error(str(exc)); st.stop()

try:
    owner, csrf, cookie = svc.session(st.session_state.get('_anonymous_cookie'))
    st.session_state['_anonymous_cookie'] = cookie
except Exception:
    st.session_state.pop('_anonymous_cookie',None)
    st.session_state.pop('_job',None)
    st.warning('会话已过期，结果与未完成任务不再可用。')
    if st.button('开始新会话'): st.rerun()
    st.stop()

st.caption('无需登录 · 每个页面会话每 30 分钟最多 4 项任务，同时 1 项；全站单机排队，最多 8 项活动任务、24 项/30 分钟。结果保留 30 分钟，会话最长 2 小时。刷新或关闭页面后可能无法恢复。')
route = st.radio('参考路线 / Reference route', ['猕猴三层 / Macaque','人类 CEL / Human'],horizontal=True)
species = 'human' if route.startswith('人类') else 'macaque'
configs = st.multiselect('冻结配置 / Frozen programs', ['RAW_FIXED','RANK_FIXED'],default=['RAW_FIXED','RANK_FIXED']) if species=='human' else ['floor_clip']
source = st.radio('输入 / Input',['上传样本 / Upload','运行现有示例 / Example'],horizontal=True)
example = None
uploaded = None
contract = False
if source.startswith('上传'):
    sample = st.text_input('样本代号 / Sample ID',value='sample_001',max_chars=128)
    st.caption('人类：Human Exon 1.0 ST CEL/CEL.gz，最大 80 MiB。猕猴：原 5000/21668 基因契约 NPZ/CSV，或完整 26,514 行 PsychENCODE 单样本 count TSV/CSV，最大 8 MiB。5000 基因输入只运行 Network。')
    uploaded = st.file_uploader('选择一个样本文件 / Choose one sample',type=['cel','gz'] if species=='human' else ['npz','csv','tsv'],max_upload_size=80 if species=='human' else 8,key='upload_'+species+'_'+str(st.session_state.get('_upload_epoch',0)))
    contract = st.checkbox('我已确认输入平台、基因标识和归一化符合对应契约。 / I confirm the input contract.')
else:
    sample='example'
    example = 'GSM755211' if species=='human' else st.selectbox('示例 / Example',['GSE128537','GSE179328','PsychENCODE_AMY','PsychENCODE_HIP'])
    st.caption('此按钮会实际运行所选单样本；示例真值仅用于结果说明。')

active = False
if st.session_state.get('_job'):
    try: active = svc.result(owner,st.session_state['_job'])['status'] in ('queued','running')
    except Exception: pass
if st.button('提交真实推断 / Run inference',type='primary',disabled=active or not configs):
    try:
        key=secrets.token_urlsafe(20)
        if source.startswith('上传'):
            if uploaded is None or not contract:
                st.warning('请选择样本并确认输入契约。'); st.stop()
            limit=(80 if species=='human' else 8)*1024**2
            if uploaded.size>limit:
                st.error('文件超过此路线的大小限制。'); st.stop()
            job=svc.submit_upload(owner,csrf,species,sample,uploaded.name,uploaded.getvalue(),configs,key)
        else:
            job=svc.submit_example(owner,csrf,species,example,configs,key)
        st.session_state['_job']=job['id']
        st.session_state['_upload_epoch']=st.session_state.get('_upload_epoch',0)+1
        st.rerun()
    except Exception as exc:
        st.error(str(exc))

@st.fragment(run_every=2 if active else None)
def result_panel():
    job_id=st.session_state.get('_job')
    if not job_id: return
    try:
        current_owner, _, _=svc.session(st.session_state['_anonymous_cookie'])
        job=svc.result(current_owner,job_id)
    except Exception:
        st.warning('会话或任务已过期。刷新后可以开始新会话。'); return
    if job['status'] in ('queued','running'):
        st.info('排队中 / Queued · 前方任务 '+str(job['queue_position']) if job['status']=='queued' else '正在运行 / Running')
        return
    if active:
        st.rerun() # Stop polling and keep the completed download frame stable.
    if job['status']=='failed':
        st.error(job['error']['message'])
        if st.button('准备下一项任务 / Next task',key='after_failure'):
            st.session_state.pop('_job',None)
            st.rerun()
        return
    result=job['result']
    st.subheader('结果 / Results')
    st.caption(result['sample_id']+' · '+result['species']+' · '+result['mode'])
    labels=svc.backend.read_json(svc.backend.ROOT/'metadata/human_labels.json') if result['species']=='human' else {}
    views=result.get('tiers',result.get('predictions',{}))
    columns=st.columns(len(views))
    for column,(tier,item) in zip(columns,views.items()):
        with column:
            st.markdown('**'+tier+'**')
            if not item.get('ranking'):
                st.warning(item.get('reason','Unavailable')); continue
            rows=[]
            for rank,cid in enumerate(item['ranking'][:3],1):
                ix=item['classes'].index(cid)
                name=labels.get(cid,cid)
                row={'Rank':rank,'Candidate':name+' ('+cid+')' if name!=cid else cid,'Score':item['scores'][ix]}
                if 'members' in item: row['Members']=', '.join(item['members'][ix])
                rows.append(row)
            # Three fixed ranks do not need a separate Arrow dataframe runtime.
            def cell(value):
                return str(value).replace('\\','\\\\').replace('|','\\|').replace('\n',' ')
            headers=list(rows[0])
            table=[' | '.join(headers),' | '.join('---' for _ in headers)]
            table += [' | '.join(cell(row[h]) for h in headers) for row in rows]
            st.markdown('\n'.join(table))
    if result['species']=='macaque':
        st.caption('Group 命中表示集合包含真值；与 Exact 单标签定位不同。分数不是已校准的正确概率。')
    else:
        st.caption('人类路线给出九个粗粒度脑区的候选排名，不包含 Group/Exact 下层。分数不是已校准的定位正确概率。')
    for warning in result.get('warnings',[]): st.caption(str(warning))
    components.html(local_download(svc.csv(current_owner,job_id),'BrainTrace_scores.csv','下载完整 CSV / Download CSV'),height=45)
    with st.expander('完整结果 / Full result'): st.json(result)
    if st.button('准备下一项任务 / Next task',key='after_success'):
        st.session_state.pop('_job',None)
        st.rerun()

result_panel()
with st.expander('输入与资源 / Input and resources'):
    st.write('PsychENCODE 适配仅用于指定的公共共同注释矩阵；分母为全部 26,514 行计数。请勿把任意 RNA-seq 矩阵当作该输入。')
    st.write('当前猕猴参考包含 43 种候选组合。缺少组合或不兼容输入会明确返回下层不可用。')
    choices=svc.backend.read_json(svc.backend.ROOT/'examples/three_tier/EXAMPLES.json')
    eid=st.selectbox('下载猕猴输入示例 / Download input example',[x['id'] for x in choices])
    item=next(x for x in choices if x['id']==eid)
    path=svc.backend.ROOT/item['input']
    components.html(local_download(path.read_bytes(),path.name,'下载所选示例 / Download example'),height=40)
    guide=st.selectbox('说明 / Guide',['INPUT_FORMATS.md','PSYCHENCODE_INPUT.md','MODEL_CARD.md','COVERAGE.md','DATA_AND_LICENSES.md'])
    guide_text=(svc.backend.ROOT/'docs'/guide).read_text(encoding='utf-8-sig')
    # Markdown files are not public Streamlit routes. Keep local cross-references
    # readable without sending visitors to a nonexistent /NAME.md page.
    guide_text=re.sub(r'\[([^\]]+)\]\((?!https?://)([^)]+\.md(?:#[^)]*)?)\)',
        lambda m: m.group(1)+' (`'+Path(m.group(2).split('#')[0]).name+'`; see Guide selector)',guide_text)
    st.markdown(guide_text)
    st.caption('输入先由 Streamlit 接收，再进入应用限额。匿名限额针对页面会话，并不能可靠识别自然人；平台客户端 IP 不用于安全身份判断。')
