"""Message envelope. Owner: A. Frozen Fri 21:00.

Every message: msg_id, src, t_created, t_expire, kind, hops, payload
kind in HB, BID, REC, OBS, CONTACT, VETO, ACK
Expiry: HB and BID 12 s; REC, OBS, CONTACT 60 s; VETO 30 s. Retry every 5 s. Max 4 hops.
Forwarding never refreshes t_created or an observation time.
"""
KINDS = ("HB", "BID", "REC", "OBS", "CONTACT", "VETO", "ACK")
