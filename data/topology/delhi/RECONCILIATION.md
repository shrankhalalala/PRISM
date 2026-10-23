# Corrected topology identity review

The six original node discrepancies have documented dispositions for a site-level reference model.
This is distinct from a fully verified current switching or electrical simulation model.

Canonical assets: **66**. Dated circuit observations: **245**.
Additional interface/section assertions: **16**; these are not additional confirmed physical circuits.

## Decisions

### IDENTITY-CANDIDATE-DWARKA

Sector-5 evacuation table explicitly names the same Dwarka–PPK-I/III, Naraina, Budella and PPK-II feeders. DPR distinguishes the new Sector-5 site from existing PPK-I. Represent the site as one complex with voltage/owner assertions; do not imply planned 66 kV works are commissioned.

- [SRC-27](https://www.dtl.gov.in/WriteReadData/userfiles/file/MOM%20of%20Steering%20Commitee%20meeting%20for%20JULY-2018%2804-07-2018%29%28PDF%29.pdf), locator: `{"physical_pages": [42, 43, 44]}`
- [SRC-24](https://forestsclearance.nic.in/DownloadPdfFile.aspx?FileName=0_0_3117123412111DPR1.pdf&FilePath=..%2Fwritereaddata%2FAddinfo%2F), locator: `{"physical_pages": [1, 2]}`
- [SRC-18](https://www.dtl.gov.in/WriteReadData/userfiles/file/MOM%20of%20Steering%20Commitee%20meeting%20for%20JUNE-2025%2825-06-2025%29%28PDF%29.pdf), locator: `{"physical_pages": [13]}`
- [SRC-01](https://www.dtl.gov.in/WriteReadData/CMS/13thBusinessPlan_2017-18_2021-22_Rev-02.pdf), locator: `{"physical_pages": [13]}`

### IDENTITY-CANDIDATE-BALLABHGARH-400

POWERGRID identifies its 400/220 kV facility at Samaypur, Ballabgarh. June 2019 DTL line table explicitly calls the endpoint Samaypur (Ballabgarh). BBMB independently lists a different 220 kV Ballabhgarh station; it is added separately.

- [SRC-23](https://apps.powergrid.in/pgciltenders/Files/1739a5ff-f1ad-41b1-a4df-7ce4f6e8dcb6/Final_published_GeM-Bidding-6416513.pdf), locator: `{"physical_pages": [13]}`
- [SRC-01](https://www.dtl.gov.in/WriteReadData/CMS/13thBusinessPlan_2017-18_2021-22_Rev-02.pdf), locator: `{"physical_pages": [31]}`
- [SRC-21](https://bbmb.gov.in/transmission-network.htm), locator: `{"section": "Sub Stations, 220 kV Ballabhgarh and Samaypur"}`

### NODE-WAZIRABAD-SITES

The 2019 DTL Wazirabad asset address matches the later directory South of Wazirabad address at Garhi/Khajuri Khas. The same Gopalpur, Mandola, Kashmere Gate and Geeta Colony connections corroborate the site mapping. Preserve Wazirabad as a source alias, not a second counted facility.

- [SRC-22](https://www.dtl.gov.in/WriteReadData/Tender/DTL-6866-290819%281%29.PDF), locator: `{"physical_pages": [133], "source_serial": 17}`
- [SRC-02](https://dtl.gov.in/content/326_1_ListofSubstations.aspx), locator: `{"table": 2, "source_serial": 37}`
- [SRC-17](https://www.dtl.gov.in/WriteReadData/userfiles/file/OCC%20Agenda%20%28pdf%29%20%28March%202026%29.pdf), locator: `{"physical_pages": [1]}`

### NODE-NARELA-SITES

BBMB describes extension of two DVB/DTL 220 kV buses. The regulator report explicitly identifies DTL and BBMB portions on an extended bus. Preserve two owner-specific assets in one reference counting group; do not count two geographically separate sites or invent a transmission line between bus sections.

- [SRC-21](https://bbmb.gov.in/transmission-network.htm), locator: `{"section": "Sub Stations, 220kV Narela"}`
- [SRC-33](https://forumofregulators.gov.in/Data/Meetings/Minutes/TC/5.pdf), locator: `{"physical_pages": [122]}`
- [SRC-25](https://www.dtl.gov.in/WriteReadData/userfiles/file/2014_Sept_Minutes.pdf), locator: `{"physical_pages": [10], "section": "2.11"}`

### NODE-BUDELLA-STATUS

June 2025 minutes identify the Budella 220/66 kV scheme as under tendering with tentative FY2028-29 commissioning. Retain the named cable observations but exclude the planned terminal from existing-asset coverage. This is dated classification, not a claim about October 2026 commissioning.

- [SRC-18](https://www.dtl.gov.in/WriteReadData/userfiles/file/MOM%20of%20Steering%20Commitee%20meeting%20for%20JUNE-2025%2825-06-2025%29%28PDF%29.pdf), locator: `{"physical_pages": [13]}`

### NODE-PLANT-TERMINALS

Station-level evacuation is documented for all four plant identities. Preserve plant assets separately from receiving substations and record known bus/transformer detail; unit-level dynamic and current breaker states remain outside topology identity acceptance.

- [SRC-31](https://www.dtl.gov.in/WriteReadData/userfiles/file/MOM%20of%20OCC%20meeting%20for%20APRIL-2026%28PDF%29.pdf), locator: `{"physical_pages": [8]}`
- [SRC-32](https://www.dtl.gov.in/WriteReadData/userfiles/file/OCC%20Agenda%20%28pdf%29%20%28July%202018%29.pdf), locator: `{"physical_pages": [7]}`
- [SRC-34](https://www.dtl.gov.in/WriteReadData/userfiles/file/MOM%20of%20OCC%20meeting%20for%20NOVEMBER-2025%28PDF%29.pdf), locator: `{"physical_pages": [7]}`
- [SRC-30](https://www.nrpc.gov.in/Meetings/OCC/OCC233/OCC233_OPA.pdf), locator: `{"physical_pages": [11], "source_rows": [89, 90]}`

## Coverage and counting

Review III physical pages 2 and 11 require 50 Delhi substation/plant nodes. Our earlier requirement for 50 geographically separate sites was stricter than the report and is corrected.
The count is 47 directory asset identities plus GTPS, PPS-I and PPS-III. It excludes the extra BBMB Narela owner portion, aliases, planned Budella and external assets. Plant/substation identities may share a complex; no count of 50 separate geographic sites is asserted.

The June 2019 schematic is reconciled to 54 asset/owner-section records; Narela has two portions under one map symbol. The original 15 historical identity differences are accounted for as aliases, single-circuit label omissions or documented LILO changes. Source length conflicts remain preserved.

The original node/circuit extraction and initial audit remain unchanged. Corrected records are in [reference_assets.csv](reference_assets.csv), with [coverage](reconciled_coverage.json) and the full [versioned dataset](reference_dataset.json).

## Remaining limits

- **NOIDA-TERMINAL**: 2019 Noida map label versus 2026 Noida Sec-86A naming needs an exact bus/station identifier; no automatic rename.
- **CIRCUIT-SUFFIXES**: Four single-circuit labels and duplicate R.K. Puram–Trauma Centre source labels remain unchanged.
- **CURRENT-SNAPSHOT**: Evidence is versioned by source date; no complete current switching snapshot established.
- **ELECTRICAL-PARAMETERS**: Flow limits, impedance, breaker states and measured node telemetry require separate evidence and are not topology identity requirements.

The 50-node source-reference coverage target is represented. Complete current network coverage, current electrical state and simulation readiness are not established by that count.
No website/model/telemetry update is included in this reconciliation.

Dataset: `delhi_reference_52179cc8a9312e8ff6141ef29fba0fa5829764be815c1b50b51d801370ea55e9`
