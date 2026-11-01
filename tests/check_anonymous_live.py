"""Two explicitly requested integration samples; no training or cohort evaluation."""
from pathlib import Path
import argparse, json, sys, threading, time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_anonymous_queue import Client
import site_server as web
import three_tier_backend as b

def main(out,work):
    out.mkdir(parents=True,exist_ok=False)
    server=web.PreviewServer(('127.0.0.1',0),work_root=work)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.1},daemon=True);thread.start()
    records=[]
    try:
        clients=[Client(server),Client(server)]
        cases=[('macaque','PsychENCODE_HIP',['floor_clip']),('human','GSM755211',['RAW_FIXED','RANK_FIXED'])]
        jobs=[]
        for c,(species,eid,configs) in zip(clients,cases):
            if species=='macaque':
                info=b.example_info(eid);path=b.ROOT/info['input'];sample='uploaded_adult_hip'
            else:path=web.FILES['human-example'];sample='uploaded_human'
            status,upload,_=c.call('/api/uploads?species='+species+'&sample_id='+sample+'&filename='+path.name,path.read_bytes())
            assert status==201,(status,upload)
            status,job,_=c.call('/api/jobs',dict(species=species,configurations=configs,source='upload',sample_id=sample,
                upload_id=upload['upload_id'],contract_confirmed=True,request_key='queue-live-'+eid))
            assert status==202,(status,job)
            jobs.append(job)
        for index,(c,case,job) in enumerate(zip(clients,cases,jobs)):
            deadline=time.monotonic()+400
            while job['status'] in ('queued','running') and time.monotonic()<deadline:
                time.sleep(.4);status,job,_=c.call('/api/jobs/'+job['id']);assert status==200
            (out/(case[1]+'_job.json')).write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
            assert job['status']=='succeeded',job.get('error')
            comparison=b.compare_example(job['result'],case[1]);assert comparison['pass'],comparison
            assert 'example_context' not in job['result'] and 'saved_output_comparison' not in job['result']
            assert clients[1-index].call('/api/jobs/'+job['id'])[0]==404
            assert clients[1-index].call('/api/jobs/'+job['id']+'/scores.csv')[0]==404
            status,csv,_=c.call('/api/jobs/'+job['id']+'/scores.csv');assert status==200
            assert csv.decode()==b.result_csv(job['result'])
            record={'sample':case[1],'species':case[0],'elapsed_seconds_including_queue':job['elapsed_seconds'],
                'comparison':comparison,'cross_session_denied':True,'unknown_upload_truth_not_added':True,'csv_exact':True}
            records.append(record);print(json.dumps(record,ensure_ascii=False),flush=True)
        assert list(work.iterdir())==[],list(work.iterdir())
        report={'sample_jobs':2,'human_configurations':2,'macaque_three_tier_jobs':1,'training':0,'cohort_rerun':False,
                'work_directory_clean':True,'checks':records}
        (out/'LIVE_QUEUE_CHECKS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--work-root',type=Path,required=True)
    args=ap.parse_args();main(args.out,args.work_root)
