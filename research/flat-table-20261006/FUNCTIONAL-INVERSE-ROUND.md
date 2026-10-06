# Functional inverse round: actual new table handoff

Original whole-flat pickup v123 remains A-only. New native behavior: loaded finger-coordinated table transport71mm, near-corner correction, passive thumb release in recorded short entry; new tilted index/middle contact; index-supported joint wrist transition followed by actual thumb slider contact. Last rail-clear short entry keeps index throughout9s, root drift0.391mm, thumb contacts slider59 recordedframes from3.567–9s. It remains table supported. Active stroke is in development; no complete A→B or generalization claim.

One continuous72.1s validation from original flat start retains clamp through64s, but prior corner release ejects knife. Actual-pose normal withdrawal also ejects it after thumb unload: loaded index requires opposition before release. Stop this passive-release branch.

Restore entries contain actual object13state, robot positions, slider, issued motor targets/history; robotvelocity finite-difference, PhysX warmstart absent. Development only, not exact resume equivalence. Actor unchanged 6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e. Original finitePD, gravity/effort/friction/resistance retained. No realrobot/realvision. Filter originalnotice preserved; no blanket experimentban established.

Reproduce from experimentroot after source runs/contact-transfer-20261006/env.sh. Run scripts/run_wuji_saved_command.py with pertrial command.json; necessary short actualstate entries and motorpaths are in progress archive. Existing A-only entry remains python -m scripts.run_wuji_flat_table_pickup_selected --output <fresh>.

Active topstroke native9s: rootdrift.336mm, slidertravel.0448mm, indexall270frames, thumb ends bodyrail. No>20mm. Newrearfaceaxialnormal approach planning; wholepadsideclearance andloadedoffset retained. GitHublatestdeadce7; topstroke evidencearchive uploaded originalReleasev2.

Rearface approach native15s fails at4.3s before rearfacecontact; indexpointgait rotates indexsurface and ejection. New index-face-retained path now planning; no gain/seed scan. Rearface failurearchive uploadedReleasev2.

Latest materialfeedback roofsliderpaced12s retains actualindex/table andslidertopcontact, drift.550mm, but travel.123mm. Normalpressure.118N andthumbjoint1issuedtarget1.6033radatupperbound. No extra gain scan. Newjointwrist/thumb-marginposture plan freesq1to1.05rad, retainingactualindexsurface+sliderpoint; currentlyplanning. Feedbacksourceedcac50and3nativefeedbackevidencearchive publishedReleasev2. Fullgoalnotcomplete.

Newphysicalmilestone: one32episode6sloadcoordinationbatch selects11.786mmdevelopmentcandidate; nativeactual-slider-coordination-selected7s confirms actualslider11.802mm (~11.89mmactiveincrease), index/thumb/table everyframe210, rootdrift7.35mm. Uses actualnewthumbmaterialpoint(.007962,.004516,-.006344) for continuedstroke nowactive; noidealreset. SearchterminalphysicslogencodingerrorfixedUTF8, no searchrerun. Not>20mmorairheldorcompleteA→B.
