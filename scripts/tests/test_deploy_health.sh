#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
TEST_DIR=$(mktemp -d)
trap 'rm -f "$TEST_DIR"/*; rmdir "$TEST_DIR"' EXIT

# Execute the actual health-check tail without running deployment commands.
export HEALTH_SECTION="$TEST_DIR/health.sh"
sed -n '/^# 10\. Health check/,$p' "$PROJECT_ROOT/deploy.sh" > "$HEALTH_SECTION"
test -s "$HEALTH_SECTION"

export MOCK_RESPONSES="$TEST_DIR/responses"
export MOCK_COUNT="$TEST_DIR/count"
export MOCK_CALLS="$TEST_DIR/calls"
export MOCK_SLEEPS="$TEST_DIR/sleeps"
export MOCK_ELAPSED="$TEST_DIR/elapsed"
export MOCK_PENDING_TIME="$TEST_DIR/pending-time"
export PRE_DEPLOY_COMMIT="test-deploy-commit"
export PRE_DEPLOY_BACKUP="/test/deployment-backup.sql.gz"

curl() {
    local connect_timeout='' request_timeout='' endpoint=''
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --connect-timeout) connect_timeout="$2"; shift 2 ;;
            --max-time) request_timeout="$2"; shift 2 ;;
            -o|--output|-w|--write-out) shift 2 ;;
            -s|-S|-sS|--silent|--show-error) shift ;;
            *) endpoint="$1"; shift ;;
        esac
    done
    printf '%s %s %s\n' "$connect_timeout" "$request_timeout" "$endpoint" >> "$MOCK_CALLS"

    local count response http_code curl_status
    read -r count < "$MOCK_COUNT"
    count=$((count + 1))
    printf '%s\n' "$count" > "$MOCK_COUNT"
    response=$(sed -n "${count}p" "$MOCK_RESPONSES")
    if [ -z "$response" ]; then
        response=$(tail -n 1 "$MOCK_RESPONSES")
    fi
    read -r http_code curl_status <<< "$response"
    printf '%s\n' "$MOCK_REQUEST_DURATION" > "$MOCK_PENDING_TIME"
    printf '%s' "$http_code"
    if [ "$curl_status" -ne 0 ]; then
        printf 'mock curl transport error %s\n' "$curl_status" >&2
    fi
    return "$curl_status"
}

sleep() {
    printf '%s\n' "$1" >> "$MOCK_SLEEPS"
    SECONDS=$((SECONDS + $1))
}

# curl runs in a substitution subshell. Apply its simulated duration when the
# main shell prints the result, before it calculates the next retry delay.
echo() {
    local request_duration
    read -r request_duration < "$MOCK_PENDING_TIME"
    SECONDS=$((SECONDS + request_duration))
    printf '0\n' > "$MOCK_PENDING_TIME"
    builtin echo "$@"
}
export -f curl sleep echo

assert_contains() {
    if [[ "$1" != *"$2"* ]]; then
        printf 'Missing expected output: %s\n%s\n' "$2" "$1" >&2
        exit 1
    fi
}

run_case() {
    local name="$1" expected_exit="$2" expected_calls="$3"
    local expected_http="$4" expected_curl="$5" responses="$6"
    local output actual_exit calls elapsed connect_timeout request_timeout endpoint last_sleep
    export MOCK_REQUEST_DURATION="${7:-0}"
    printf '%s\n' "$responses" > "$MOCK_RESPONSES"
    printf '0\n' > "$MOCK_COUNT"
    printf '0\n' > "$MOCK_PENDING_TIME"
    : > "$MOCK_CALLS"
    : > "$MOCK_SLEEPS"

    if output=$(bash -c '
        set -e
        # Remove the special timer attribute so mocks control all elapsed time.
        unset SECONDS
        SECONDS=0
        trap '\''printf "%s\n" "$SECONDS" > "$MOCK_ELAPSED"'\'' EXIT
        source "$HEALTH_SECTION"
    ' 2>&1); then
        actual_exit=0
    else
        actual_exit=$?
    fi

    if [ "$actual_exit" -ne "$expected_exit" ]; then
        printf '%s returned %s, expected %s\n%s\n' "$name" "$actual_exit" "$expected_exit" "$output" >&2
        exit 1
    fi
    read -r calls < "$MOCK_COUNT"
    read -r elapsed < "$MOCK_ELAPSED"
    test "$calls" -ge 1
    test "$calls" -le 13
    test "$elapsed" -le 61
    if [ "$expected_calls" -gt 0 ]; then
        test "$calls" -eq "$expected_calls"
    fi
    while read -r connect_timeout request_timeout endpoint; do
        test "$connect_timeout" -eq 3
        test "$request_timeout" -ge 1
        test "$request_timeout" -le 5
        test "$endpoint" = "http://localhost:8002/api/health/"
    done < "$MOCK_CALLS"
    assert_contains "$output" "$PRE_DEPLOY_COMMIT"
    assert_contains "$output" "$PRE_DEPLOY_BACKUP"

    if [ "$expected_exit" -eq 0 ]; then
        assert_contains "$output" '部署成功'
        assert_contains "$output" '健康检查: OK'
    else
        test "$calls" -gt 1
        test "$elapsed" -ge 60
        [[ "$output" != *'部署成功'* ]]
        assert_contains "$output" '部署失败'
        assert_contains "$output" "HTTP 状态码: $expected_http"
        assert_contains "$output" "curl 退出码: $expected_curl"
        assert_contains "$output" 'docker compose logs backend'
        if [ "$expected_curl" -ne 0 ]; then
            assert_contains "$output" "mock curl transport error $expected_curl"
        fi
    fi
    if [ "$expected_calls" -eq 1 ]; then
        test ! -s "$MOCK_SLEEPS"
    fi
    if [ "$MOCK_REQUEST_DURATION" -gt 0 ]; then
        read -r connect_timeout request_timeout endpoint < <(tail -n 1 "$MOCK_CALLS")
        read -r last_sleep < <(tail -n 1 "$MOCK_SLEEPS")
        test "$request_timeout" -lt 5
        test "$last_sleep" -lt 5
    fi
    printf 'PASS %s\n' "$name"
}

run_case 'first request succeeds' 0 1 200 0 '200 0'
run_case 'HTTP 503 then recovery' 0 2 200 0 $'503 0\n200 0'
run_case 'connection error then recovery' 0 2 200 0 $'000 7\n200 0'
run_case 'persistent HTTP 503' 1 0 503 0 '503 0'
run_case 'persistent connection errors' 1 0 000 7 '000 7'
run_case 'persistent request timeouts' 1 0 000 28 '000 28'
run_case 'HTTP 200 with failed transfer' 1 0 200 28 '200 28'
run_case 'request and sleep shrink near deadline' 1 0 503 0 '503 0' 2
printf '8 deployment health scenarios passed.\n'
