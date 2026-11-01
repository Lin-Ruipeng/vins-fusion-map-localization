#!/usr/bin/env python
"""Acceptance evidence and plots from real messages and actual map events.

Works with the Python 2/numpy/matplotlib bundled in the pinned ROS image.
Ground truth is used here, strictly after estimation, for evaluation only.
"""
from __future__ import print_function
import csv
import json
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LAB = '/work'
run_name = sys.argv[1] if len(sys.argv) > 1 else 'mh02_localization'
run = LAB + '/results/' + run_name
run_invocation=json.load(open(run+'/invocation.json'))
assert run_invocation['sequence']=='MH_02_easy' and run_invocation['load'] and not run_invocation['save'], 'MH02 localization run required'
session=json.load(open(run+'/session_summary.json'))
assert session['run_status']=='sensor_replay_and_pose_capture_complete', 'Replay did not finish'
assert all(code==0 for code in session['process_exit_codes'].values()), 'A runtime node failed'
bag_validation=json.load(open(run+'/bag_export_validation.json'))
assert all(bag_validation[name]['max_live_bag_component_error']==0.
           for name in ['vio_odometry.csv','map_odometry.csv']), 'CSV/bag discrepancy'

def read_poses(name):
    with open(run + '/' + name, 'rb') as f:
        rows = list(csv.DictReader(f))
    stamps = np.array([int(row['timestamp_ns']) for row in rows], dtype=np.int64)
    wall = np.array([float(row['receive_wall_s']) for row in rows])
    values = np.array([[float(row[k]) for k in ['px','py','pz','qx','qy','qz','qw']] for row in rows])
    assert len(stamps) > 20
    assert np.all(np.diff(stamps) > 0), 'Non-monotonic pose timestamp'
    assert np.all(np.isfinite(values)), 'Non-finite pose'
    assert np.max(np.abs(np.linalg.norm(values[:,3:], axis=1)-1.)) < 1e-5, 'Invalid quaternion'
    return stamps, wall, values

def events(log):
    result = []
    for line in open(log):
        if '[MAPLAB]' not in line:
            continue
        kind = line.split('[MAPLAB] ',1)[1].split()[0]
        fields = dict(re.findall(r'(\w+)=([^\s\x1b]+)', line))
        for k in list(fields):
            try:
                fields[k] = float(fields[k])
            except ValueError:
                pass
        fields['event'] = kind
        result.append(fields)
    return result

ev = events(run + '/loop.log')
loaded = [e for e in ev if e['event']=='MAP_LOADED' and e['keyframes'] > 0]
connections = [e for e in ev if e['event']=='PNP_ACCEPT' and e['old_sequence']==0 and e['current_sequence']==1]
alignments = [e for e in ev if e['event']=='CROSS_SEQUENCE_ALIGN' and e['old_sequence']==0 and e['current_sequence']==1]
assert loaded, 'Map was not actually loaded'
assert connections, 'No geometrically accepted connection to the saved map'
assert all(0<=e['old']<loaded[0]['keyframes'] and e['current']>=loaded[0]['keyframes']
           for e in connections), 'Connection does not reference a loaded keyframe'
assert alignments, 'No first cross-sequence alignment'
assert 'Initialization finish!' in open(run + '/vins.log').read(), 'VIO did not initialize'
first = alignments[0]
assert any(e['current']==first['current'] and e['old']==first['old'] and e['inliers']>25 for e in connections)
ns, wall, raw = read_poses('vio_odometry.csv')
mns, mwall, corrected = read_poses('map_odometry.csv')
assert np.array_equal(ns,mns), 'VIO/map timestamps differ or messages were dropped'
post = mwall > first['wall'] + 0.2
assert np.count_nonzero(post)>100, 'Insufficient output after alignment'
dt = np.diff(mns[post].astype(np.float64))/1e9
gaps = []
for left,right in zip(connections,connections[1:]):
    if right['wall']-left['wall'] > 0.5:
        mask=(mwall>left['wall']+0.05)&(mwall<right['wall']-0.05)&post
        gaps.append((np.count_nonzero(mask),right['wall']-left['wall'],left,right,mask))
assert gaps, 'Need at least two saved-map connections to verify inter-match output'
gap=max(gaps,key=lambda g:g[1])
assert gap[0]>=5, 'No continuous poses between saved-map PnP events'

yaw=np.deg2rad(first['yaw_deg'])
alignment_rotation=np.array([[np.cos(yaw),-np.sin(yaw),0.],[np.sin(yaw),np.cos(yaw),0.],[0.,0.,1.]])
alignment_translation=np.array([first['tx'],first['ty'],first['tz']])
frozen=raw[:,:3].dot(alignment_rotation.T)+alignment_translation
seconds=(ns.astype(np.float64)-float(ns[0]))/1e9

summary={'sequence':json.load(open(run+'/invocation.json'))['sequence'],
    'map_loaded_keyframes':int(loaded[0]['keyframes']),
    'accepted_connections_to_loaded_sequence':len(connections),
    'first_alignment':first,
    'first_connection':[e for e in connections if e['current']==first['current']][0],
    'local_pose_count':len(raw),'corrected_pose_count':len(corrected),
    'poses_after_first_alignment':int(np.count_nonzero(post)),
    'pose_frame':'body/IMU; position and quaternion orientation',
    'sensor_time_output_hz':float((len(mns)-1)*1e9/(mns[-1]-mns[0])),
    'post_alignment_median_interval_s':float(np.median(dt)),
    'post_alignment_max_interval_s':float(np.max(dt)),
    'longest_saved_map_match_gap':{'wall_duration_s':gap[1],
       'corrected_pose_messages_between_matches':int(gap[0]),
       'left_event':gap[2],'right_event':gap[3]},
    'initialization_confirmed':True,'vio_and_map_message_timestamps_identical':True,
    'finite_positions_and_unit_quaternions':True,
    'ground_truth_used_for_estimation':False}

invocation=json.load(open(run+'/invocation.json'))
map_rows=np.loadtxt(LAB+'/maps/'+invocation.get('map_name','mh01')+'/pose_graph.txt')
map_t=map_rows[:,1]
map_positions=map_rows[:,5:8]
gt1=np.loadtxt(LAB+'/data/MH_01_easy/mav0/state_groundtruth_estimate0/data.csv',delimiter=',',comments='#')
gt2=np.loadtxt(LAB+'/data/MH_02_easy/mav0/state_groundtruth_estimate0/data.csv',delimiter=',',comments='#')
gt1_t,gt2_t=gt1[:,0]/1e9,gt2[:,0]/1e9
valid=(map_t>=gt1_t[0])&(map_t<=gt1_t[-1])
x=np.column_stack([np.interp(map_t[valid],gt1_t,gt1[:,k]) for k in [1,2,3]])
y=map_positions[valid]
U,S,Vt=np.linalg.svd((x-x.mean(0)).T.dot(y-y.mean(0)))
R=Vt.T.dot(U.T)
if np.linalg.det(R)<0:
    Vt[-1,:]*=-1
    R=Vt.T.dot(U.T)
t=y.mean(0)-R.dot(x.mean(0))
fit_rmse=float(np.sqrt(np.mean(np.sum((x.dot(R.T)+t-y)**2,axis=1))))
stamp_s=ns.astype(np.float64)/1e9
gt2_interpolated=np.column_stack([np.interp(stamp_s,gt2_t,gt2[:,k]) for k in [1,2,3]])
gtmap=gt2_interpolated.dot(R.T)+t
evaluation=post&(stamp_s>=gt2_t[0])&(stamp_s<=gt2_t[-1])
rect_error=np.linalg.norm(corrected[:,:3]-gtmap,axis=1)
frozen_error=np.linalg.norm(frozen-gtmap,axis=1)
summary['evaluation']={'reference':'One SE3, scale=1 fit of MH01 ground-truth body positions to saved MH01 optimized keyframes; same transform applied unchanged to MH02 ground truth. MH02 raw VIO uses only its first actual map alignment, frozen thereafter.',
    'gt_to_map_rotation':R.tolist(),'gt_to_map_translation':t.tolist(),
    'mh01_reference_fit_position_rmse_m':fit_rmse,
    'mh02_post_alignment_corrected_position_rmse_m':float(np.sqrt(np.mean(rect_error[evaluation]**2))),
    'mh02_first_alignment_frozen_vio_position_rmse_m':float(np.sqrt(np.mean(frozen_error[evaluation]**2))),
    'post_alignment_evaluation_samples':int(np.count_nonzero(evaluation)),
    'mh02_poses_fitted_to_ground_truth':False}
assert np.count_nonzero(evaluation)>100

fig,axes=plt.subplots(2,2,figsize=(13,10))
ax=axes[0,0]
ax.plot(map_positions[:,0],map_positions[:,1],color='.65',lw=1,label='Saved MH01 map')
ax.plot(gtmap[evaluation,0],gtmap[evaluation,1],'k--',lw=1,label='MH02 GT (MH01 reference only)')
ax.plot(frozen[evaluation,0],frozen[evaluation,1],color='#16834b',lw=1,label='MH02 VIO + frozen first alignment')
ax.plot(corrected[post,0],corrected[post,1],color='#c93635',lw=1,label='MH02 continuous map pose')
ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('Map x [m]');ax.set_ylabel('Map y [m]')
ax.set_title('Body/IMU trajectory in saved-map coordinates');ax.legend(fontsize=8,loc='best');ax.grid(alpha=.25)
ax=axes[0,1]
for k,label in enumerate(['x','y','z']):
    ax.plot(seconds[post],corrected[post,k],lw=.8,label='map '+label)
ax.axvline(seconds[np.flatnonzero(post)[0]],color='k',ls=':',lw=1)
ax.set_xlabel('MH02 sensor time since first VIO pose [s]');ax.set_ylabel('Position [m]')
ax.set_title('Continuous map position after first old-map alignment');ax.legend(fontsize=8);ax.grid(alpha=.25)
ax=axes[1,0]
ax.plot(seconds[evaluation],frozen_error[evaluation],color='#16834b',label='VIO + frozen first alignment')
ax.plot(seconds[evaluation],rect_error[evaluation],color='#c93635',label='Continuous map pose')
ax.set_title('Position error: one common reference, no MH02 GT fit');ax.set_xlabel('Sensor time [s]');ax.set_ylabel('Position error [m]')
ax.legend(fontsize=8);ax.grid(alpha=.25)
ax=axes[1,1]
change=np.linalg.norm(corrected[:,:3]-frozen,axis=1)
ax.plot(seconds[post],change[post],color='#714eb5',lw=1)
event_times=[(e['stamp']*1e9-float(ns[0]))/1e9 for e in connections]
ax.plot(event_times,np.zeros(len(event_times)),'|',color='#d88412',markersize=8,label='Accepted old-map PnP')
ax.set_title('Later correction relative to frozen first alignment')
ax.set_xlabel('Sensor time [s]');ax.set_ylabel('Position difference [m]');ax.legend(fontsize=8);ax.grid(alpha=.25)
fig.suptitle('VINS-Fusion: MH01 saved map + MH02 stereo/IMU replay',fontsize=14)
fig.tight_layout(rect=[0,0,1,.96]);fig.savefig(run+'/trajectory_comparison.png',dpi=160);plt.close(fig)

# A real long interval without a map match, with every output pose visible.
moving_gaps=[]
for candidate in gaps:
    mask=candidate[4]
    positions=corrected[mask,:3]
    quaternions=corrected[mask,3:]
    span=float(np.max(np.linalg.norm(positions-positions[0],axis=1)))
    angular_span=float(np.max(2*np.arccos(np.minimum(1.,np.abs(quaternions.dot(quaternions[0])))))*180/np.pi)
    if candidate[0]>=5 and span>0.2 and angular_span>1.:
        moving_gaps.append((candidate,span,angular_span))
if moving_gaps:
    gap,span,angular_span=max(moving_gaps,key=lambda g:g[0][1])
    local_positions=raw[gap[4],:3]
    summary['moving_saved_map_match_gap']={
        'wall_duration_s':gap[1],'corrected_pose_messages_between_matches':int(gap[0]),
        'maximum_map_position_change_m':span,'maximum_orientation_change_deg':angular_span,
        'maximum_raw_vio_position_change_m':float(np.max(np.linalg.norm(local_positions-local_positions[0],axis=1))),
        'left_event':gap[2],'right_event':gap[3]}
mask=gap[4]
timebase=gap[2]['wall']
fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True)
for k,label in enumerate(['x','y','z']):
    axes[0].plot(mwall[mask]-timebase,corrected[mask,k],'.-',ms=2,lw=.6,label=label)
for k,label in enumerate(['qx','qy','qz','qw']):
    axes[1].plot(mwall[mask]-timebase,corrected[mask,k+3],'.-',ms=2,lw=.6,label=label)
indices=np.flatnonzero(mask)
axes[2].plot(mwall[mask]-timebase,np.arange(len(indices)),'.',ms=3,color='#c93635')
for ax in axes:
    ax.axvline(0,color='#d88412',ls='--');ax.axvline(gap[1],color='#d88412',ls='--');ax.grid(alpha=.25)
axes[0].set_ylabel('Position [m]');axes[0].legend(fontsize=8,ncol=3)
axes[1].set_ylabel('Unit quaternion');axes[1].legend(fontsize=8,ncol=4)
axes[2].set_ylabel('Continuous map messages');axes[2].set_xlabel('Wall time since preceding old-map PnP [s]')
fig.suptitle('%d actual poses during %.2f s between two accepted saved-map PnP events' % (gap[0],gap[1]),fontsize=12)
fig.tight_layout(rect=[0,0,1,.96]);fig.savefig(run+'/continuity_evidence.png',dpi=160);plt.close(fig)
summary['acceptance_passed']=True
summary['run_name']=run_name
summary['map_name']=invocation.get('map_name','mh01')
summary['verification_created_wall_s']=__import__('time').time()
open(run+'/verification.json','w').write(json.dumps(summary,indent=2))
open(run+'/events.json','w').write(json.dumps(ev,indent=2))
print(json.dumps(summary,indent=2))
