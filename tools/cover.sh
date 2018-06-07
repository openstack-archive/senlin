#!/bin/bash
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This tool is borrowed from the Rally / Manila projects and revised to enhance
# Senlin coverage test.

ALLOWED_EXTRA_MISSING=4
TESTR_ARGS="$*"

show_diff () {
    head -1 $1
    diff -U 0 $1 $2 | sed 1,2d
}

if ! git diff --exit-code || ! git diff --cached --exit-code
then
    echo "There are uncommitted changes!"
    echo "Please clean git working directory and try again"
    exit 1
fi

# Checkout master and save coverage report
git checkout HEAD^

baseline_report=$(mktemp -t senlin_coverageXXXXXXX)
find . -type f -name "*.py[c|o]" -delete && stestr run "$TESTR_ARGS" && coverage combine && coverage html -d cover
coverage report --ignore-errors > $baseline_report
cat $baseline_report
if [ -d "cover-master" ]; then
    rm -rf cover-master
fi
mv cover cover-master
baseline_missing=$(awk 'END { print $3 }' $baseline_report)

# Checkout back and save coverage report
git checkout -

# Generate and save coverage report
current_report=$(mktemp -t senlin_coverageXXXXXXX)
find . -type f -name "*.py[c|o]" -delete && stestr run "$TESTR_ARGS" && coverage combine && coverage html -d cover
coverage report --ignore-errors > $current_report
cat $current_report
current_missing=$(awk 'END { print $3 }' $current_report)

# Show coverage details
allowed_missing=$((baseline_missing+ALLOWED_EXTRA_MISSING))

echo "Allowed to introduce missing lines : ${ALLOWED_EXTRA_MISSING}"
echo "Missing lines in master            : ${baseline_missing}"
echo "Missing lines in proposed change   : ${current_missing}"

if [ $allowed_missing -gt $current_missing ];
then
    if [ $baseline_missing -lt $current_missing ];
    then
        show_diff $baseline_report $current_report
        echo "I believe you can cover all your code with 100% coverage!"
    else
        echo "Thank you! You are awesome! Keep writing unit tests! :)"
    fi
    exit_code=0
else
    show_diff $baseline_report $current_report
    echo "Please write more unit tests, we should keep our test coverage :( "
    exit_code=1
fi

rm $baseline_report $current_report
exit $exit_code
