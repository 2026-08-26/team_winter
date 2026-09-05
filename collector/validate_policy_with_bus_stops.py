from pathlib import Path
import sys

import pandas as pd


# =========================================================
# 1. 경로
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)


# 버스정류소 병합 전
BEFORE_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대반영.csv"
)


# 버스정류소 병합 후
AFTER_FILE = (
    PROCESSED_DIR
    / "청년주거환경_정책통합분석_공공시설_공공임대_버스정류소반영.csv"
)


# =========================================================
# 2. 기대값
# =========================================================

EXPECTED_REGION_COUNT = 25

EXPECTED_STOP_TOTAL = 570

EXPECTED_ROUTE_MATCH_RATE = 0.54


EXPECTED_CANDIDATES = {

    "서구 금호1동",

    "북구 첨단2동",

    "광산구 수완동",

    "남구 진월동",

    "북구 용봉동",

    "광산구 우산동"
}


errors = []
warnings = []


# =========================================================
# 3. 도움 함수
# =========================================================

def add_error(message):

    errors.append(
        message
    )


def add_warning(message):

    warnings.append(
        message
    )


def to_bool(value):

    if isinstance(
        value,
        bool
    ):

        return value


    text = str(
        value
    ).strip().lower()


    return text in [

        "true",
        "1",
        "yes",
        "y"

    ]


# =========================================================
# 4. 시작
# =========================================================

print()

print(
    "=" * 60
)

print(
    "공식 버스정류소 정책통합 최종 품질검사"
)

print(
    "=" * 60
)


# =========================================================
# 5. 파일 존재 확인
# =========================================================

if not BEFORE_FILE.exists():

    print()
    print(
        "병합 전 정책통합 파일이 없습니다."
    )

    print(
        BEFORE_FILE
    )

    sys.exit(1)


if not AFTER_FILE.exists():

    print()
    print(
        "버스정류소 병합 후 파일이 없습니다."
    )

    print(
        AFTER_FILE
    )

    sys.exit(1)


# =========================================================
# 6. 파일 읽기
# =========================================================

before = pd.read_csv(
    BEFORE_FILE,
    encoding="utf-8-sig"
)


after = pd.read_csv(
    AFTER_FILE,
    encoding="utf-8-sig"
)


# =========================================================
# 7. 지역 수 확인
# =========================================================

if len(
    before
) != EXPECTED_REGION_COUNT:

    add_error(
        f"병합 전 지역 수가 25개가 아닙니다. "
        f"현재 {len(before)}개"
    )


if len(
    after
) != EXPECTED_REGION_COUNT:

    add_error(
        f"병합 후 지역 수가 25개가 아닙니다. "
        f"현재 {len(after)}개"
    )


# =========================================================
# 8. 지역 중복 확인
# =========================================================

if before[
    "지역"
].duplicated().any():

    add_error(
        "병합 전 파일에 중복 지역이 있습니다."
    )


if after[
    "지역"
].duplicated().any():

    add_error(
        "병합 후 파일에 중복 지역이 있습니다."
    )


# =========================================================
# 9. 지역 목록 유지 확인
# =========================================================

before_regions = set(
    before[
        "지역"
    ]
)


after_regions = set(
    after[
        "지역"
    ]
)


if before_regions != after_regions:

    add_error(
        "버스정류소 병합 과정에서 "
        "25개 지역 목록이 변경되었습니다."
    )


# =========================================================
# 10. 기존 정책 데이터가 바뀌지 않았는지 확인
# =========================================================

before_sorted = (

    before

    .sort_values(
        "지역"
    )

    .reset_index(
        drop=True
    )

)


after_sorted = (

    after

    .sort_values(
        "지역"
    )

    .reset_index(
        drop=True
    )

)


existing_columns = list(
    before.columns
)


missing_old_columns = [

    column

    for column
    in existing_columns

    if column
    not in after.columns

]


if missing_old_columns:

    add_error(
        "기존 컬럼이 사라졌습니다 : "
        + ", ".join(
            missing_old_columns
        )
    )


else:

    try:

        pd.testing.assert_frame_equal(

            before_sorted[
                existing_columns
            ],

            after_sorted[
                existing_columns
            ],

            check_dtype=False,

            check_exact=False,

            rtol=1e-10,

            atol=1e-10

        )


    except AssertionError:

        add_error(
            "버스정류소 병합 과정에서 "
            "기존 정책분석 값이 변경되었습니다."
        )


# =========================================================
# 11. 필수 버스 컬럼
# =========================================================

required_columns = [

    "공식정류소수",

    "청년1000명당_정류소수",

    "정류소공급_상대부족",

    "청년교통공급_점검후보",

    "버스정류소_정책보조해석",

    "정책_교통공급_통합신호",

    "버스정류소_HL반영여부",

    "버스노선데이터_안전매칭률",

    "버스노선데이터_활용판정",

    "버스노선_정책분석사용여부",

    "버스노선_제외사유",

    "버스정류소_정책유형변경여부"
]


missing = [

    column

    for column
    in required_columns

    if column
    not in after.columns

]


if missing:

    add_error(
        "버스정류소 필수 컬럼 누락 : "
        + ", ".join(
            missing
        )
    )


# =========================================================
# 아래 검사는 필수 컬럼 존재 시 진행
# =========================================================

if not missing:


    # =====================================================
    # 12. 숫자 변환
    # =====================================================

    after[
        "공식정류소수"
    ] = pd.to_numeric(
        after[
            "공식정류소수"
        ],
        errors="coerce"
    )


    after[
        "청년1000명당_정류소수"
    ] = pd.to_numeric(
        after[
            "청년1000명당_정류소수"
        ],
        errors="coerce"
    )


    after[
        "버스노선데이터_안전매칭률"
    ] = pd.to_numeric(
        after[
            "버스노선데이터_안전매칭률"
        ],
        errors="coerce"
    )


    # =====================================================
    # 13. Boolean 변환
    # =====================================================

    bool_columns = [

        "정류소공급_상대부족",

        "청년교통공급_점검후보",

        "버스정류소_HL반영여부",

        "버스노선_정책분석사용여부",

        "버스정류소_정책유형변경여부"
    ]


    for column in bool_columns:

        after[
            column
        ] = (

            after[
                column
            ]

            .apply(
                to_bool
            )

        )


    # =====================================================
    # 14. 공식 정류소 총합
    # =====================================================

    total_stops = int(

        after[
            "공식정류소수"
        ]

        .fillna(0)

        .sum()

    )


    if total_stops != EXPECTED_STOP_TOTAL:

        add_error(
            f"25개 동 공식 정류소 합계가 "
            f"{EXPECTED_STOP_TOTAL}개가 아닙니다. "
            f"현재 {total_stops}개"
        )


    # =====================================================
    # 15. 중앙값 검사
    # =====================================================

    stop_median = (

        after[
            "청년1000명당_정류소수"
        ]

        .median()

    )


    if abs(
        stop_median
        -
        4.69
    ) > 0.01:

        add_warning(
            f"청년 1,000명당 정류소 중앙값이 "
            f"직전 4.69와 다릅니다. "
            f"현재 {stop_median:.2f}"
        )


    # =====================================================
    # 16. 상대부족 판정 검사
    # =====================================================

    expected_shortage = (

        after[
            "청년1000명당_정류소수"
        ]

        < stop_median

    )


    shortage_mismatch = after[
        expected_shortage
        !=
        after[
            "정류소공급_상대부족"
        ]
    ]


    if not shortage_mismatch.empty:

        add_error(
            "정류소 상대부족 판정 불일치 : "
            + ", ".join(
                shortage_mismatch[
                    "지역"
                ].tolist()
            )
        )


    # =====================================================
    # 17. 청년교통공급 후보 조건 확인
    #
    # 기존 2030 TOP10
    # +
    # 정류소 공급 상대부족
    # =====================================================

    if (
        "2030인구_TOP10"
        not in after.columns
    ):

        add_error(
            "2030인구_TOP10 컬럼이 없습니다."
        )


    else:

        after[
            "2030인구_TOP10"
        ] = (

            after[
                "2030인구_TOP10"
            ]

            .apply(
                to_bool
            )

        )


        expected_candidate = (

            after[
                "2030인구_TOP10"
            ]

            &

            after[
                "정류소공급_상대부족"
            ]

        )


        candidate_mismatch = after[
            expected_candidate
            !=
            after[
                "청년교통공급_점검후보"
            ]
        ]


        if not candidate_mismatch.empty:

            add_error(
                "청년교통공급 점검후보 "
                "조건 불일치 : "
                + ", ".join(
                    candidate_mismatch[
                        "지역"
                    ].tolist()
                )
            )


    # =====================================================
    # 18. 후보 6곳 확인
    # =====================================================

    actual_candidates = set(

        after[
            after[
                "청년교통공급_점검후보"
            ]
            == True
        ][
            "지역"
        ]

    )


    if actual_candidates != EXPECTED_CANDIDATES:

        add_error(
            "청년교통공급 점검후보가 "
            "직전 결과와 다릅니다. "
            f"현재: {sorted(actual_candidates)}"
        )


    # =====================================================
    # 19. 버스 노선 안전 매칭률
    # =====================================================

    match_rates = (

        after[
            "버스노선데이터_안전매칭률"
        ]

        .dropna()

        .unique()

    )


    if len(
        match_rates
    ) != 1:

        add_error(
            "버스 노선 안전 매칭률 값이 "
            "지역별로 서로 다릅니다."
        )


    else:

        match_rate = float(
            match_rates[0]
        )


        if abs(
            match_rate
            -
            EXPECTED_ROUTE_MATCH_RATE
        ) > 0.01:

            add_error(
                f"노선 안전 매칭률이 "
                f"0.54%가 아닙니다. "
                f"현재 {match_rate:.2f}%"
            )


    # =====================================================
    # 20. 노선 데이터 미사용 확인
    # =====================================================

    if (
        after[
            "버스노선_정책분석사용여부"
        ]
        .any()
    ):

        add_error(
            "버스 노선 데이터가 "
            "정책분석에 사용된 지역이 있습니다."
        )


    # =====================================================
    # 21. HL 미반영 확인
    # =====================================================

    if (
        after[
            "버스정류소_HL반영여부"
        ]
        .any()
    ):

        add_error(
            "공식 정류소 보조지표가 "
            "HL-Score에 반영된 지역이 있습니다."
        )


    # =====================================================
    # 22. 기존 정책유형 미변경 확인
    # =====================================================

    if (
        after[
            "버스정류소_정책유형변경여부"
        ]
        .any()
    ):

        add_error(
            "버스정류소 데이터 때문에 "
            "기존 정책유형이 변경된 지역이 있습니다."
        )


    # =====================================================
    # 23. 두암2동 유지 확인
    # =====================================================

    duam = after[
        after[
            "지역"
        ]
        == "북구 두암2동"
    ]


    if len(
        duam
    ) != 1:

        add_error(
            "북구 두암2동을 "
            "정확히 찾을 수 없습니다."
        )


    else:

        policy_type = str(

            duam.iloc[0][
                "최종정책유형"
            ]

        ).strip()


        if policy_type != "HL순위 제외":

            add_error(
                "두암2동의 HL순위 제외 상태가 "
                "변경되었습니다."
            )


    # =====================================================
    # 24. 6개 후보가 기존 정책신호인지 확인
    # =====================================================

    no_existing_signal = []


    for region in EXPECTED_CANDIDATES:

        row = after[
            after[
                "지역"
            ]
            == region
        ]


        if len(
            row
        ) != 1:

            continue


        policy_type = str(

            row.iloc[0][
                "최종정책유형"
            ]

        ).strip()


        if policy_type in [

            "",
            "일반 관찰",
            "HL순위 제외"

        ]:

            no_existing_signal.append(
                region
            )


    if no_existing_signal:

        add_warning(
            "교통 점검후보 중 기존 정책신호가 "
            "없는 지역이 있습니다 : "
            + ", ".join(
                no_existing_signal
            )
        )


# =========================================================
# 25. 검사 요약
# =========================================================

print()
print(
    "-" * 60
)

print(
    "검사 요약"
)

print(
    "-" * 60
)


print(
    f"병합 전 지역 : "
    f"{len(before)}개"
)


print(
    f"병합 후 지역 : "
    f"{len(after)}개"
)


if (
    "공식정류소수"
    in after.columns
):

    print(
        f"25개 동 공식 정류소 : "
        f"{int(pd.to_numeric(after['공식정류소수'], errors='coerce').fillna(0).sum()):,}개"
    )


if (
    "청년교통공급_점검후보"
    in after.columns
):

    candidate_rows = after[

        after[
            "청년교통공급_점검후보"
        ].apply(
            to_bool
        )

    ]


    print(
        f"청년교통공급 점검후보 : "
        f"{len(candidate_rows)}개"
    )


    for region in candidate_rows[
        "지역"
    ].tolist():

        print(
            "-",
            region
        )


# =========================================================
# 26. 최종 결과
# =========================================================

print()
print(
    "=" * 60
)

print(
    "최종 품질검사 결과"
)

print(
    "=" * 60
)


if warnings:

    print()
    print(
        "[주의]"
    )

    for warning in warnings:

        print(
            "!",
            warning
        )


if errors:

    print()
    print(
        "[검사 실패]"
    )

    for error in errors:

        print(
            "X",
            error
        )


    print()
    print(
        f"총 오류 : "
        f"{len(errors)}개"
    )


    print()
    print(
        "버스정류소 정책통합 품질검사 : FAIL"
    )

    sys.exit(1)


else:

    print()
    print(
        "모든 핵심 검사 통과"
    )

    print(
        "25개 동 공식 정류소 570개가 "
        "정상 연결되었습니다."
    )

    print(
        "청년교통공급 점검후보 "
        "6개 지역도 정상입니다."
    )

    print(
        "기존 HL-Score와 정책유형은 "
        "변경되지 않았습니다."
    )

    print(
        "버스 노선 데이터는 "
        "안전 매칭률 0.54%로 "
        "정책분석에서 제외된 상태입니다."
    )

    print(
        "두암2동 HL순위 제외 상태도 "
        "정상 유지되었습니다."
    )


    if not warnings:

        print(
            "추가 경고사항도 없습니다."
        )


    print()
    print(
        "버스정류소 정책통합 품질검사 : PASS"
    )