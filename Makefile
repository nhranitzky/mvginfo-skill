REPO=nhranitzky/mvginfo-cli
CLI=mvginfo/scripts/mvginfo

dl-cli:
	rm -rf $(CLI) && npx degit $(REPO)/mvginfo $(CLI)

commit:
	git add -A
	git commit -m "$(MSG)"

push:
	git push
