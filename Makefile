
dl-cli:
	npx degit nhranitzky/mvginfo-cli/mvginfo mvginfo/scripts/mvginfo

commit:
	git add -A
	git commit -m "$(MSG)"

push:
	git push
